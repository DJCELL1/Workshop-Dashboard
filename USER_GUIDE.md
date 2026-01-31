# HDL Locksmiths Workshop Dashboard - User Guide

**For: Deb, Jared, and Elvis**

---

## What This Dashboard Shows

The Workshop Dashboard displays all **active locksmith jobs** from Cin7 that need attention. Jobs are organized into sections based on their stage and due date (ETD):

### Currently Working On Section (Top of Dashboard)

| Section | What It Means |
|---------|---------------|
| **🔨 Currently Working On** | Jobs in "Processing" stage - actively being worked on. These are displayed prominently at the top so everyone can see what's in progress. Cards scroll horizontally if there are many. |

### Main Board Columns (Below Currently Working On)

| Column | What It Means |
|--------|---------------|
| **🔴 Overdue** | ETD date has passed - needs urgent attention! |
| **🟡 Due Soon** | Due within the next 7 days |
| **🟢 On Track** | Has an ETD date more than 7 days away |
| **⚪ No ETD** | No estimated delivery date set yet |

**Note:** Jobs in "Processing" stage appear in the "Currently Working On" section at the top and are NOT shown in the main columns below.

---

## How Jobs Appear on the Dashboard

For a Sales Order to show up on this dashboard, it must have:

### Required Fields in Cin7:

1. **Distribution Branch** = `Locksmiths`
   - This is the most important field!
   - Found at the bottom of the Sales Order screen
   - If this isn't set to "Locksmiths", the job won't appear

2. **Stage** = One of these:
   - `New` - Job just created
   - `Processing` - Currently being worked on (shows in "Currently Working On" section)
   - `Job Complete` - Finished, waiting for dispatch

3. **ETD (Estimated Delivery Date)** - Optional but recommended
   - This determines which column the job appears in
   - Without an ETD, jobs go to the "No ETD" column
   - Set this to when the job should be completed

### Fields That Display on Job Cards:

- **Reference** - The Sales Order number (e.g., SO-4856)
- **Project Name** - What the job is for (e.g., "Rekey unit 208")
- **Company** - Customer name
- **Created Date** - When the order was created
- **ETD** - When it's due

---

## How to Create a Job That Shows on the Dashboard

### In Cin7, when creating or editing a Sales Order:

1. **Set the Distribution Branch to "Locksmiths"**
   - Scroll to the bottom of the Sales Order
   - Click on "Distribution Branch"
   - Select "Locksmiths"

2. **Set the Stage appropriately**
   - New job? Set to `New`
   - Starting work? Change to `Processing`
   - Finished the work? Change to `Job Complete`

3. **Set the ETD Date**
   - Click on the ETD field
   - Enter when the job should be completed
   - This helps prioritize work on the dashboard

4. **Fill in Project Name** (recommended)
   - This shows on the job card
   - Makes it easy to identify what the job is

5. **Save the Sales Order**

---

## Changing Stages as Work Progresses

### Stage Workflow:

```
New  -->  Processing  -->  Job Complete  -->  Fully Dispatched
 |            |                |                    |
 |            |                |                    |
Shows on   Shows in        Shows on            REMOVED from
dashboard  "Currently      dashboard           dashboard
           Working On"                         (job done!)
```

### How to Change Stage in Cin7:

1. Open the Sales Order
2. Find the **Stage** dropdown (usually on the right side)
3. Select the new stage:
   - **New** - Job is waiting to be started
   - **Processing** - You're actively working on it
   - **Job Complete** - Work is done, ready for dispatch
   - **Fully Dispatched** - Job is complete and delivered (removes from dashboard)

4. Click **Save**

### When to Change Stages:

| When... | Change Stage To... |
|---------|-------------------|
| Job comes in | `New` |
| You start working on it | `Processing` |
| Work is finished | `Job Complete` |
| Customer has received it | `Fully Dispatched` |

---

## Understanding the Dashboard Colors

### Job Card Colors:

- **Red border** = OVERDUE - ETD has passed, urgent!
- **Yellow/Amber border** = Due within 7 days
- **Green border** = On track, ETD is more than 7 days away
- **Gray border** = No ETD set

### Badges on Cards:

- `OVERDUE` (red) - Shows how many days overdue
- `DUE SOON` (yellow) - Due within 7 days
- `ON TRACK` (green) - Plenty of time
- `NO ETD` (gray) - No due date set
- `Processing` / `New` / `Job Complete` - Current stage

---

## Tips for Using the Dashboard

1. **Check it daily** - Start your day by looking at Overdue and Due Soon columns

2. **Keep ETD dates updated** - If a job is delayed, update the ETD in Cin7

3. **Move jobs to Processing** - When you start working on something, change the stage so others know

4. **Use the Search box** - Quickly find a specific job by typing the reference, project name, or customer

5. **Click Refresh** - If you've just updated something in Cin7, click the refresh button to see changes (data caches for 5 minutes)

---

## Quick Reference - Required Settings

| Field | Where to Find It | What to Set |
|-------|------------------|-------------|
| Distribution Branch | Bottom of Sales Order | **Locksmiths** |
| Stage | Right side dropdown | New / Processing / Job Complete |
| ETD | Top of Sales Order | Due date for the job |
| Project Name | Top of Sales Order | Description of the job |

---

## Troubleshooting

**Job not showing on dashboard?**
- Check Distribution Branch is set to "Locksmiths"
- Check Stage is New, Processing, or Job Complete
- Wait 5 minutes or click Refresh (data is cached)

**Job showing in wrong column?**
- Check/update the ETD date in Cin7

**Need to remove a completed job?**
- Change Stage to "Fully Dispatched" in Cin7

---

*Dashboard auto-refreshes data every 5 minutes. Click the Refresh button for immediate updates.*
