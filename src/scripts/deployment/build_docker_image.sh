#!/bin/bash
#
# Docker Image Build Script for Budget Management Application
#
# This script builds a Docker image for the Budget Management Application, 
# optionally scans it for vulnerabilities, and pushes it to Google Container Registry.
#
# Usage:
#   ./build_docker_image.sh [options]
#
# For detailed usage information, run:
#   ./build_docker_image.sh -h

# Get script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Source the shell template
source "$SCRIPT_DIR/../../templates/shell_template.sh"

# Default global variables (can be overridden via environment variables or command-line args)
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
APP_NAME=${APP_NAME:-budget-management}
VERSION=${VERSION:-latest}
DOCKERFILE_PATH=${DOCKERFILE_PATH:-$ROOT_DIR/src/backend/Dockerfile}
CONTEXT_PATH=${CONTEXT_PATH:-$ROOT_DIR/src/backend}
REGISTRY=${REGISTRY:-gcr.io}
PUSH_IMAGE=${PUSH_IMAGE:-false}
SCAN_IMAGE=${SCAN_IMAGE:-false}
BUILD_ARGS=${BUILD_ARGS:-}
IMAGE_TAG=${IMAGE_TAG:-$REGISTRY/$PROJECT_ID/$APP_NAME:$VERSION}
LATEST_TAG=${LATEST_TAG:-$REGISTRY/$PROJECT_ID/$APP_NAME:latest}

#
# Functions
#

# Check if Docker is installed and accessible
check_docker_installed() {
    log_debug "Checking if Docker is installed..."
    
    if ! check_command_exists "docker"; then
        log_error "Docker is not installed or not in PATH. Please install Docker."
        return 1
    fi
    
    # Verify Docker is running by checking version
    if ! docker --version > /dev/null 2>&1; then
        log_error "Docker is installed but not running or not accessible."
        return 1
    fi
    
    local docker_version=$(docker --version)
    log_debug "Docker is installed: $docker_version"
    
    return 0
}

# Check if gcloud CLI is installed and configured if pushing to GCR
check_gcloud_installed() {
    # Skip check if not pushing to GCR
    if [[ "$PUSH_IMAGE" != "true" ]]; then
        return 0
    fi
    
    log_debug "Checking if gcloud CLI is installed..."
    
    if ! check_command_exists "gcloud"; then
        log_error "gcloud CLI is not installed or not in PATH. Please install Google Cloud SDK."
        return 1
    fi
    
    # Verify gcloud is properly installed by checking version
    if ! gcloud --version > /dev/null 2>&1; then
        log_error "gcloud CLI is installed but not accessible."
        return 1
    fi
    
    # Check if project is configured
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "$current_project" ]]; then
        log_error "No Google Cloud project is configured. Please run 'gcloud init' or set PROJECT_ID."
        return 1
    fi
    
    log_debug "gcloud CLI is installed and configured with project: $current_project"
    
    return 0
}

# Check if Trivy is installed for vulnerability scanning
check_trivy_installed() {
    # Skip check if not scanning
    if [[ "$SCAN_IMAGE" != "true" ]]; then
        return 0
    fi
    
    log_debug "Checking if Trivy is installed..."
    
    if ! check_command_exists "trivy"; then
        log_error "Trivy is not installed or not in PATH. Please install Trivy for vulnerability scanning."
        return 1
    fi
    
    # Verify Trivy is properly installed by checking version
    if ! trivy --version > /dev/null 2>&1; then
        log_error "Trivy is installed but not accessible."
        return 1
    fi
    
    local trivy_version=$(trivy --version)
    log_debug "Trivy is installed: $trivy_version"
    
    return 0
}

# Build the Docker image
build_docker_image() {
    log_info "Starting Docker image build..."
    
    # Check if Dockerfile exists
    if [[ ! -f "$DOCKERFILE_PATH" ]]; then
        log_error "Dockerfile not found at: $DOCKERFILE_PATH"
        return 1
    fi
    
    # Check if context directory exists
    if [[ ! -d "$CONTEXT_PATH" ]]; then
        log_error "Context directory not found at: $CONTEXT_PATH"
        return 1
    fi
    
    log_info "Building image: $IMAGE_TAG"
    log_debug "Using Dockerfile: $DOCKERFILE_PATH"
    log_debug "Using context: $CONTEXT_PATH"
    
    # Construct build command
    local build_cmd="docker build -t \"$IMAGE_TAG\""
    
    # Add latest tag if version is not "latest"
    if [[ "$VERSION" != "latest" ]]; then
        build_cmd="$build_cmd -t \"$LATEST_TAG\""
    fi
    
    # Add Dockerfile path
    build_cmd="$build_cmd -f \"$DOCKERFILE_PATH\""
    
    # Add build args if specified
    if [[ -n "$BUILD_ARGS" ]]; then
        for arg in $BUILD_ARGS; do
            build_cmd="$build_cmd --build-arg \"$arg\""
        done
    fi
    
    # Add context path
    build_cmd="$build_cmd \"$CONTEXT_PATH\""
    
    # Execute build with retry
    log_debug "Build command: $build_cmd"
    if ! retry_command "$build_cmd"; then
        log_error "Docker image build failed."
        return 1
    fi
    
    log_info "Docker image built successfully: $IMAGE_TAG"
    return 0
}

# Scan the Docker image for vulnerabilities using Trivy
scan_docker_image() {
    # Skip if scanning is not enabled
    if [[ "$SCAN_IMAGE" != "true" ]]; then
        return 0
    fi
    
    log_info "Scanning image for vulnerabilities..."
    
    # Create temporary directory for Trivy cache if it doesn't exist
    local trivy_cache_dir="/tmp/trivy-cache"
    mkdir -p "$trivy_cache_dir"
    
    # Run Trivy scan
    # Using a non-zero exit code for critical vulnerabilities
    log_debug "Running Trivy scan on image: $IMAGE_TAG"
    
    if ! trivy image --cache-dir "$trivy_cache_dir" --severity HIGH,CRITICAL "$IMAGE_TAG"; then
        log_error "Vulnerability scan failed or critical vulnerabilities found."
        
        # Provide guidance in case of vulnerabilities
        log_error "Please review the vulnerabilities and fix them before proceeding."
        log_error "For non-critical environments, you can bypass this check with SCAN_IMAGE=false."
        
        return 1
    fi
    
    log_info "Vulnerability scan completed. No critical vulnerabilities found."
    return 0
}

# Push the Docker image to Google Container Registry
push_docker_image() {
    # Skip if pushing is not enabled
    if [[ "$PUSH_IMAGE" != "true" ]]; then
        return 0
    fi
    
    log_info "Pushing image to registry: $REGISTRY/$PROJECT_ID/$APP_NAME:$VERSION"
    
    # Configure Docker to use gcloud as a credential helper for GCR
    log_debug "Configuring Docker authentication with Google Container Registry..."
    if ! gcloud auth configure-docker --quiet; then
        log_error "Failed to configure Docker authentication with GCR."
        return 1
    fi
    
    # Push the versioned tag
    log_debug "Pushing image: $IMAGE_TAG"
    if ! retry_command "docker push \"$IMAGE_TAG\""; then
        log_error "Failed to push image to registry."
        return 1
    fi
    
    # Also push the latest tag if version is not "latest"
    if [[ "$VERSION" != "latest" ]]; then
        log_debug "Pushing latest tag: $LATEST_TAG"
        if ! retry_command "docker push \"$LATEST_TAG\""; then
            log_error "Failed to push latest tag to registry."
            return 1
        fi
    fi
    
    log_info "Image successfully pushed to registry."
    return 0
}

# Generate a version tag based on semantic versioning and git commit
generate_version_tag() {
    log_debug "Generating version tag based on git history..."
    
    local git_tag=""
    local git_commit=""
    
    # Try to get the latest git tag
    if git describe --tags --abbrev=0 2>/dev/null; then
        git_tag=$(git describe --tags --abbrev=0 2>/dev/null)
    fi
    
    # Get the short git commit hash
    git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    # Construct version tag
    local version_tag=""
    if [[ -n "$git_tag" ]]; then
        # Remove 'v' prefix if present
        local version="${git_tag#v}"
        version_tag="$version-$git_commit"
    else
        # Default to 0.1.0 if no git tags found
        version_tag="0.1.0-$git_commit"
    fi
    
    log_debug "Generated version tag: $version_tag"
    echo "$version_tag"
}

# Parse custom command line arguments
parse_custom_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --project-id)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "Option --project-id requires an argument."
                    return 1
                fi
                PROJECT_ID="$2"
                shift 2
                ;;
            --app-name)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "Option --app-name requires an argument."
                    return 1
                fi
                APP_NAME="$2"
                shift 2
                ;;
            --version)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "Option --version requires an argument."
                    return 1
                fi
                VERSION="$2"
                shift 2
                ;;
            --dockerfile)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "Option --dockerfile requires an argument."
                    return 1
                fi
                DOCKERFILE_PATH="$2"
                shift 2
                ;;
            --context)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "Option --context requires an argument."
                    return 1
                fi
                CONTEXT_PATH="$2"
                shift 2
                ;;
            --registry)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "Option --registry requires an argument."
                    return 1
                fi
                REGISTRY="$2"
                shift 2
                ;;
            --push)
                PUSH_IMAGE="true"
                shift
                ;;
            --scan)
                SCAN_IMAGE="true"
                shift
                ;;
            --build-arg)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "Option --build-arg requires an argument."
                    return 1
                fi
                if [[ -z "$BUILD_ARGS" ]]; then
                    BUILD_ARGS="$2"
                else
                    BUILD_ARGS="$BUILD_ARGS $2"
                fi
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                return 1
                ;;
        esac
    done
    
    # Update derived variables after parsing arguments
    IMAGE_TAG="$REGISTRY/$PROJECT_ID/$APP_NAME:$VERSION"
    LATEST_TAG="$REGISTRY/$PROJECT_ID/$APP_NAME:latest"
    
    return 0
}

# Display custom help information
show_custom_help() {
    echo "CUSTOM OPTIONS:"
    echo "  --project-id VALUE    Set the Google Cloud project ID (default: from gcloud config)"
    echo "  --app-name VALUE      Set the application name (default: budget-management)"
    echo "  --version VALUE       Set the image version tag (default: latest, use 'auto' for git-based versioning)"
    echo "  --dockerfile VALUE    Set the path to the Dockerfile (default: $ROOT_DIR/src/backend/Dockerfile)"
    echo "  --context VALUE       Set the build context directory (default: $ROOT_DIR/src/backend)"
    echo "  --registry VALUE      Set the container registry (default: gcr.io)"
    echo "  --push                Enable pushing the image to the registry"
    echo "  --scan                Enable vulnerability scanning with Trivy"
    echo "  --build-arg VALUE     Add a build argument (can be used multiple times)"
    echo
    echo "DESCRIPTION:"
    echo "  Builds a Docker image for the Budget Management Application, optionally"
    echo "  scans it for vulnerabilities, and pushes it to Google Container Registry."
    echo
    echo "EXAMPLES:"
    echo "  # Build the image with default settings"
    echo "  $SCRIPT_NAME"
    echo
    echo "  # Build and push to Google Container Registry"
    echo "  $SCRIPT_NAME --push"
    echo
    echo "  # Build with a specific version tag and scan for vulnerabilities"
    echo "  $SCRIPT_NAME --version 1.0.0 --scan"
    echo
    echo "  # Build with custom project and application name"
    echo "  $SCRIPT_NAME --project-id my-project --app-name my-app"
}

# Main function that orchestrates the Docker image build process
main() {
    log_info "Starting Docker image build process for Budget Management Application"
    
    # Check if Docker is installed
    if ! check_docker_installed; then
        return 1
    fi
    
    # Check if gcloud is installed if pushing
    if [[ "$PUSH_IMAGE" == "true" ]] && ! check_gcloud_installed; then
        return 1
    fi
    
    # Check if Trivy is installed if scanning
    if [[ "$SCAN_IMAGE" == "true" ]] && ! check_trivy_installed; then
        return 1
    fi
    
    # Generate version tag if auto
    if [[ "$VERSION" == "auto" ]]; then
        VERSION=$(generate_version_tag)
        IMAGE_TAG="$REGISTRY/$PROJECT_ID/$APP_NAME:$VERSION"
        LATEST_TAG="$REGISTRY/$PROJECT_ID/$APP_NAME:latest"
        log_info "Using auto-generated version tag: $VERSION"
    fi
    
    # Build the Docker image
    if ! build_docker_image; then
        return 1
    fi
    
    # Scan the image if requested
    if ! scan_docker_image; then
        return 1
    fi
    
    # Push the image if requested
    if ! push_docker_image; then
        return 1
    fi
    
    log_info "Docker image build process completed successfully"
    log_info "Image: $IMAGE_TAG"
    
    if [[ "$PUSH_IMAGE" == "true" ]]; then
        log_info "Image pushed to: $REGISTRY/$PROJECT_ID/$APP_NAME"
    fi
    
    return 0
}