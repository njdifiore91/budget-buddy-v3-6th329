```
I want to create an application that will help me manage my budget. 
Overall objectives:
- Compare my spending habits to the spending habits outlined in my budget
- Identify areas where my spending has been lower than or greater than allotted amounts in the master budget sheet
- Generate a concise email based on a Gemini prompt to summarize my spending habits for the week, making sure to specifically highlight the amount remaining or amount over budget I am at the very top.
- Initiate a transaction via Capital One API to deposit any amount which is left over from my weekly budget into a separate savings account.
Key documents: 
- “Master Budget”: Google sheet representing my budget - contains a list of categories and corresponding dollar amounts on a weekly biweekly monthly and yearly basis, corresponding to the budgeted amount of money spent in each category in those specific periods.
    - Columns: 
        - Spending Category: The spending category (e.g. Groceries, Rent, Electric, Charity)
        - Weekly Amount: Amount of weekly spending allotted for that spending category
- “Weekly Spending”: Google sheet that tracks money spent on a weekly basis, tracked from transactions through CapitalOne API
    - Columns: 
        - Transaction Location: location of the transaction
        - Transaction Amount: Amount of the transaction in US dollars
        - Transaction Time: Time of the transaction, Eastern Standard Time
        - Corresponding Category: The category of spending, determined by Gemini API call and selecting from the list of Categories in the Master Budget sheet
Integrations:
- CapitalOne API:
    - Each time the job runs, this integration will:
        - 1. Extract transactions from one specific checking account in my CapitalOne account (specified in the code) from that past week, and populate the Weekly Spending Google Sheet
        - 2. Initiate a transaction that takes the amount I did not spend in my weekly budget and sends it to a separate savings account. This should be well documented in the code showcasing what is happening
- Google Sheets API:
    - Each time the job runs, this integration will: 
        - Extract information from the CapitalOne transactions and populate the Weekly Budget sheet’s following columns: Transaction Location, Transaction Amount, Transaction Time
- Gemini API: 
    - Each time the job runs, this integration will:
        - 1. Take the “Transaction Location” column and attempt to correspond it to one of the categories in the “Master Budget” sheet.
        - 2. Craft a summary email summarizing my spending habits for the week, making sure to specifically highlight the amount remaining or amount over budget I am at the very top of the email and in the subject line. Also will contain charts. 
- Gmail API: 
    - Each time the job runs, this integration will:
        - Take the summary email written by Gemini and send from njdifiore@gmail.com to the specified email addresses: njdifiore@gmail.com, nick@blitzy.com
Overall data/information steps:
1. Google Cloud run job runs
2. Weekly transactions extracted from CapitalOne API and populate Weekly Spending Google Sheet
3. Call to Gemini API takes the “Transaction Location” column and attempts to correspond it to one of the categories in the “Master Budget” sheet
4. Call to Gemini API compares spending per category in Weekly Spending sheet to allotted spending in Master Budget sheet, writing summary email to capture this
5. V ia Gmail API, Gemini’s summary email is sent from njdifiore@gmail.com to njdifiore@gmail.com and nick@blitzy.com 
Infrastructure/implementation:
- This will be a job based application executed through Google Cloud run jobs. The job will run every Sunday at 12 PM Eastern standard time.
Front End:
- There will be no front end. This is a backend only application that will be run entirely via Google Cloud Run jobs or the command line. If we want to run the job on an ad-hoc basis, we should be able to run the file via our CLI and have the job execute automatically.
```