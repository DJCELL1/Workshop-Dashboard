# HDL Workshop Capacity Board - User Manual

## Overview

The Workshop Capacity Board is a visual dashboard that displays all active Locksmith workshop jobs from Cin7. It helps the team see at a glance:
- What jobs are currently being worked on
- Which jobs need ETD dates added
- What's overdue, due soon, or on track

The dashboard has two views:
- **Desktop View** - Full-featured view with search, filters, and data export
- **TV View** - Simplified 3-column view optimized for the workshop TV display

---

## For Order Entry (Deb & Sean)

When entering orders into Cin7, there are **two critical fields** you must set correctly for the Workshop Board to work:

### 1. Distribution Branch

**⚠️ IMPORTANT:** You must select the correct Distribution Branch for the order to appear on the Workshop Board.

| Field | Required Value |
|-------|----------------|
| **Distribution Branch** | `Locksmiths` |

If you don't set this, the job **will not appear** on the Workshop Board.

**How to set it in Cin7:**
1. Open the Sales Order
2. Find the "Distribution Branch" field
3. Select **"Locksmiths"** from the dropdown
4. Save the order

### 2. Estimated Delivery Date (ETD)

**⚠️ IMPORTANT:** Always set an ETD date so the workshop knows when the job is due.

| Field | What to Enter |
|-------|---------------|
| **Estimated Delivery Date** | The date the job needs to be completed/dispatched |

**Why this matters:**
- Jobs without an ETD appear in the "📅 Needs ETD" section
- The workshop can't prioritise work properly without knowing due dates
- Jobs with ETD dates are automatically sorted into Overdue/Due Soon/On Track columns

**How to set it in Cin7:**
1. Open the Sales Order
2. Find the "Estimated Delivery Date" field
3. Enter the date the customer needs the job completed
4. Save the order

### Quick Checklist for Order Entry

✅ Distribution Branch set to **Locksmiths**
✅ Estimated Delivery Date entered
✅ Project Name filled in (helps identify the job)
✅ Company name correct

---

## For Workshop (Jared & Elvis)

The Workshop Board helps you see what needs to be worked on and track progress. Your main responsibility is **updating the Stage** in Cin7 as you work on jobs.

### Understanding the Board Layout

The Desktop View has several highlighted sections displayed in order of priority:

#### 🔧 Currently in Workshop (Green Section)
- Shows all jobs in **"Processing"** stage
- This is what the workshop is actively working on right now
- Scrolls horizontally if there are many jobs

#### 📦 To Collect (Purple Section)
- Shows all jobs in **"To Collect"** stage
- These are completed jobs waiting for customer pickup
- Scrolls horizontally if there are many jobs

#### 🚨 Overdue (Red Section)
- Shows all jobs past their ETD date
- Sorted by most overdue first - needs urgent attention!
- Scrolls horizontally if there are many jobs

#### 📅 Needs ETD (Dark Section)
- Shows jobs that don't have a due date set
- These need Deb/Sean to add an ETD date
- Sorted by oldest first (longest waiting)

#### 🟠 Jobs in Queue
- Shows jobs due within the next 7 days that are not yet in Processing
- These are the upcoming jobs that should be worked on next

### Updating Job Status in Cin7

**⚠️ CRITICAL:** You must update the Stage in Cin7 for the board to reflect your work accurately.

#### Stage Workflow

```
New → Processing → Job Complete → Fully Dispatched
                 ↘ To Collect → Fully Dispatched
```

| Stage | When to Use |
|-------|-------------|
| **New** | Order has been entered, not started yet |
| **Processing** | You are actively working on this job |
| **Job Complete** | Work is done, ready for dispatch |
| **To Collect** | Work is done, customer will pick up (not for delivery) |
| **Fully Dispatched** | Job has been sent/collected by customer (removes from board) |

#### How to Update the Stage in Cin7

1. Open the Sales Order in Cin7
2. Find the "Stage" field
3. Change it to the appropriate stage:
   - Set to **"Processing"** when you start working on a job
   - Set to **"Job Complete"** when the work is finished
4. Save the order

**💡 TIP:** When you start your day, look at the "Currently Working On" section to see what's marked as Processing. If you're starting a new job, remember to update its stage to "Processing" in Cin7!

### Reading the Job Cards

Each job card shows:

```
┌─────────────────────────────┐
│ SO-12345          (Reference)
│ Customer Project Name
│ Company Name
│ ┌─────────┐ ┌───────────┐
│ │ OVERDUE │ │ Processing│  (Status badges)
│ └─────────┘ └───────────┘
│ ETD: 15 Jan 2025
│ Created: 10 Jan 2025
└─────────────────────────────┘
```

- **Reference**: The Cin7 Sales Order number
- **Project Name**: What the job is for
- **Company**: The customer
- **Status Badge**: Shows urgency (Overdue/Due Soon/On Track/No ETD)
- **Stage Badge**: Current workflow stage
- **ETD**: When it's due
- **Created**: When the order was entered

**Tip:** Click on any job card to open the Sales Order directly in Cin7!

### Colour Coding

| Colour | Meaning |
|--------|---------|
| 🔴 Red border | Overdue - past due date |
| 🟡 Amber border | Due within 7 days |
| 🟢 Green border | On track - due later |
| ⚪ Gray border | No ETD date set |

---

## Using the Dashboard

### Refresh Data
- Click the **🔄 Refresh** button to get the latest data from Cin7
- Data is cached for 5 minutes to reduce API calls
- The page auto-refreshes every 12 hours to keep data current

### Search
- Use the search box to find specific jobs
- Searches by: Reference number, Project Name, or Company name

### Filter by Stage
- Use the "Stages" dropdown to show/hide different stages
- Default shows: New, Processing, Job Complete

### Filter by Date Range
- Toggle "Show only next 30 days" to focus on upcoming work

### Export Data
- Scroll down to the "Detailed View" section
- Click **📥 Download CSV** to export the data to Excel

---

## TV View (Workshop Display)

The TV View is designed for the workshop TV display. Switch to it by clicking the **📺 TV View** tab at the top of the dashboard.

### TV View Features
- **Large text** readable from across the workshop
- **4-column layout** showing the most important information:
  - **OVERDUE** (Red) - Jobs past their due date
  - **IN WORKSHOP** (Green) - Jobs currently being worked on
  - **TO COLLECT** (Purple) - Jobs ready for customer pickup
  - **COMING UP** (Orange) - Jobs due within 7 days
- **KPI cards** showing total counts at a glance
- **Auto-refresh** keeps the display current

### TV View Layout
```
┌────────────────────────────────────────────────────────────────────────┐
│  [Logo] Workshop Board                                  10:30  Monday  │
├────────────────────────────────────────────────────────────────────────┤
│  OVERDUE: 2  │  IN WORKSHOP: 3  │  TO COLLECT: 1  │  IN QUEUE: 5      │
├────────────────────────────────────────────────────────────────────────┤
│   OVERDUE    │   IN WORKSHOP    │   TO COLLECT    │    COMING UP      │
│ ┌──────────┐ │  ┌──────────┐    │  ┌──────────┐   │   ┌──────────┐    │
│ │ Job Card │ │  │ Job Card │    │  │ Job Card │   │   │ Job Card │    │
│ └──────────┘ │  └──────────┘    │  └──────────┘   │   └──────────┘    │
│ ┌──────────┐ │  ┌──────────┐    │                 │   ┌──────────┐    │
│ │ Job Card │ │  │ Job Card │    │                 │   │ Job Card │    │
│ └──────────┘ │  └──────────┘    │                 │   └──────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```

The TV view shows up to 6 jobs per column. If there are more jobs, a "+X more" indicator appears.

---

## Troubleshooting

### Job not appearing on the board?
1. Check the **Distribution Branch** is set to "Locksmiths"
2. Check the **Stage** is not "Fully Dispatched" or "Cancelled"
3. Click **Refresh** to reload data
4. Wait a few minutes and try again (data caches for 5 mins)

### Job stuck in wrong column?
1. Check the **ETD date** is correct in Cin7
2. Check the **Stage** is correct in Cin7
3. Click **Refresh** to reload data

### Can't see "Currently Working On" section?
- This section only appears if there are jobs in "Processing" stage
- Make sure to update jobs to "Processing" when you start work

### Data seems outdated?
- Click the **🔄 Refresh** button
- Data is cached for 5 minutes to reduce API calls
- The page auto-refreshes every 12 hours

### Can't click on job cards to open Cin7?
- Job cards link to Cin7 - clicking should open the Sales Order
- Make sure pop-ups are enabled for the dashboard site
- If on the TV View, cards are display-only (not clickable)

---

## Quick Reference

### For Deb & Sean (Order Entry)
| Action | What to Do |
|--------|------------|
| New order | Set Distribution Branch to **Locksmiths** |
| Set due date | Enter **Estimated Delivery Date** |

### For Jared & Elvis (Workshop)
| Action | What to Do |
|--------|------------|
| Starting a job | Change Stage to **Processing** |
| Finished a job (for delivery) | Change Stage to **Job Complete** |
| Finished a job (customer pickup) | Change Stage to **To Collect** |
| Job dispatched/collected | Change Stage to **Fully Dispatched** |

---

## Support

If you have issues with the Workshop Board, contact the IT team.

**Timezone:** Pacific/Auckland (NZ time)
**Data Cache:** 5 minutes
**Auto-Refresh:** Every 12 hours
**Version:** 1.2
