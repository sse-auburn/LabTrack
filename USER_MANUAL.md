# LabTrack User Manual

This manual documents every feature and workflow in LabTrack for both members and administrators. Read the section that matches your role, then refer to specific workflow sections as needed.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
   - [Logging In](#11-logging-in)
   - [Registering an Account](#12-registering-an-account)
   - [User Roles](#13-user-roles)
   - [The Dashboard](#14-the-dashboard)
   - [Navigation](#15-navigation)
2. [Your Profile](#2-your-profile)
   - [Viewing Your Profile](#21-viewing-your-profile)
   - [Editing Your Profile](#22-editing-your-profile)
   - [Changing Your Password](#23-changing-your-password)
   - [Notification Preferences](#24-notification-preferences)
3. [Equipment](#3-equipment)
   - [Browsing and Searching Equipment](#31-browsing-and-searching-equipment)
   - [Viewing Equipment Details](#32-viewing-equipment-details)
   - [Registering New Equipment](#33-registering-new-equipment)
   - [Equipment Approval](#34-equipment-approval)
   - [Editing Equipment](#35-editing-equipment)
   - [Moving Equipment Between Locations](#36-moving-equipment-between-locations)
   - [Recording Lifecycle Events](#37-recording-lifecycle-events)
   - [Deactivating Equipment](#38-deactivating-equipment)
   - [Categories and Locations](#39-categories-and-locations)
4. [Borrowing](#4-borrowing)
   - [Submitting a Borrow Request](#41-submitting-a-borrow-request)
   - [Borrow Request Status Reference](#42-borrow-request-status-reference)
   - [Viewing Your Active Borrows](#43-viewing-your-active-borrows)
   - [Submitting a Return](#44-submitting-a-return)
   - [Confirming a Return (Equipment Owner)](#45-confirming-a-return-equipment-owner)
   - [Kit Borrow Returns](#46-kit-borrow-returns)
   - [Overdue Items](#47-overdue-items)
5. [Reservations](#5-reservations)
   - [Creating a Reservation](#51-creating-a-reservation)
   - [Reservation Status Reference](#52-reservation-status-reference)
   - [Viewing Your Reservations](#53-viewing-your-reservations)
   - [Calendar View](#54-calendar-view)
   - [Cancelling a Reservation](#55-cancelling-a-reservation)
   - [Submitting a Reservation Return](#56-submitting-a-reservation-return)
   - [Confirming a Reservation Return (Equipment Owner)](#57-confirming-a-reservation-return-equipment-owner)
   - [The Waitlist](#58-the-waitlist)
6. [Kits](#6-kits)
   - [Creating a Kit](#61-creating-a-kit)
   - [Adding Items to a Kit](#62-adding-items-to-a-kit)
   - [Sharing a Kit](#63-sharing-a-kit)
   - [Borrowing a Kit](#64-borrowing-a-kit)
   - [Returning a Kit](#65-returning-a-kit)
   - [Editing and Deleting Kits](#66-editing-and-deleting-kits)
7. [Consumables](#7-consumables)
   - [Browsing Consumables](#71-browsing-consumables)
   - [Logging Consumable Usage](#72-logging-consumable-usage)
   - [Adding a New Consumable (Admin)](#73-adding-a-new-consumable-admin)
   - [Restocking a Consumable (Admin)](#74-restocking-a-consumable-admin)
   - [Low-Stock List (Admin)](#75-low-stock-list-admin)
8. [Incidents](#8-incidents)
   - [Reporting an Incident](#81-reporting-an-incident)
   - [Incident Status Reference](#82-incident-status-reference)
   - [Assigning an Investigator](#83-assigning-an-investigator)
   - [Resolving an Incident](#84-resolving-an-incident)
   - [Closing an Incident](#85-closing-an-incident)
   - [Maintenance Logs](#86-maintenance-logs)
   - [Calibration Logs](#87-calibration-logs)
9. [Projects](#9-projects)
   - [Creating a Project](#91-creating-a-project)
   - [Managing Project Members](#92-managing-project-members)
   - [Updating Project Status](#93-updating-project-status)
10. [Notifications](#10-notifications)
    - [In-App Notifications](#101-in-app-notifications)
    - [Email Notifications](#102-email-notifications)
    - [Notification Events Reference](#103-notification-events-reference)
11. [Activity Log](#11-activity-log)
12. [Admin Guide](#12-admin-guide)
    - [First-Time Setup](#121-first-time-setup)
    - [Managing Members](#122-managing-members)
    - [Assigning Roles](#123-assigning-roles)
    - [Admin Dashboard](#124-admin-dashboard)
    - [Admin Panel](#125-admin-panel)
    - [Approving Pending Equipment](#126-approving-pending-equipment)
    - [Return Queue](#127-return-queue)
    - [Overdue Borrow Detection](#128-overdue-borrow-detection)
    - [Django Back-Office](#129-django-back-office)

---

## 1. Getting Started

### 1.1 Logging In

1. Open LabTrack in your browser. The root URL (`/`) redirects to the dashboard.
2. If you are not logged in you are redirected to the login page (`/accounts/login/`).
3. Enter your **email address** and **password**.
4. Click **Log In**.

If you forget your password, contact a LabTrack administrator — there is no self-service password reset. Administrators can set a new password for you through the Django back-office.

### 1.2 Registering an Account

If registration is open at your lab:

1. Go to `/accounts/register/`.
2. Fill in your **email address**, **username**, and **password** (confirmed twice).
3. Click **Register**.

Your account is created immediately, but you will have no role until an administrator assigns one. Until then you can log in but cannot access any module.

> **Administrators:** New self-registered accounts appear in the Members list. Assign them a role before they can use the system.

### 1.3 User Roles

LabTrack has two roles:

| Role | Access |
|---|---|
| **Member** | Browse and borrow equipment; create reservations; manage their own kits; log consumable usage; report incidents; create projects |
| **Admin** | Everything a Member can do, plus: manage users and roles; approve/reject equipment registrations; view the activity log; access the admin panel; perform any action on any record |

Roles are assigned by an administrator from the Members page.
A superuser created with `createsuperuser` automatically has the Admin role.

### 1.4 The Dashboard

After login you land on the dashboard, which differs by role.

**Member dashboard:**
- Stats bar: your active borrows, pending return approvals, active reservations, active projects
- **My Active Borrows** — equipment and kits you currently have checked out, with due dates
- **My Pending Returns** — items you have submitted for return that are awaiting owner confirmation
- **Pending Return Approvals** — items whose owner you are, awaiting your confirmation
- **My Reservations** — upcoming and active reservations
- **My Kits** — your personal kits
- **Recent Activity** — your last 10 actions in the system

**Admin dashboard:**
- Stats bar: total equipment, active borrows, pending returns, low-stock consumables, open incidents
- **Overdue Borrows** alert — appears when any borrow is past its due date
- **Low Stock Consumables** alert — appears when any consumable is at or below its threshold
- Quick actions: Browse Equipment, New Borrow, New Reservation, Return Queue, Consumables, Incidents
- Charts: equipment by status, monthly borrow activity
- **Recent Members** — last 5 registered users

### 1.5 Navigation

The left sidebar (collapsed on mobile with the hamburger menu) links to every module. The top bar shows:

- The **notification bell** with an unread count badge — click to open the notification drawer
- Your **avatar / username** — click to access your profile or log out

---

## 2. Your Profile

### 2.1 Viewing Your Profile

Click your username or avatar in the top bar, then **Profile**, or navigate to `/accounts/profile/`.

The profile page shows:
- Your name, email, username, role, and date joined
- Contact information (phone, department, student ID)
- Bio
- Profile photo
- Your current notification preferences (summary)

### 2.2 Editing Your Profile

From the profile page click **Edit Profile**, or go to `/accounts/profile/edit/`.

You can update:
- **First and last name**
- **Phone number**
- **Department**
- **Student ID**
- **Bio**
- **Profile photo** (JPEG/PNG, max 20 MB)

Click **Save Changes** to apply.

### 2.3 Changing Your Password

From your profile page click **Change Password** (or `/accounts/password/change/`).

1. Enter your **current password**.
2. Enter and confirm your **new password**.
3. Click **Change Password**.

You remain logged in after the change.

### 2.4 Notification Preferences

From the profile edit page, scroll to **Notification Preferences**.

**Global toggles:**
- **In-app notifications** — when disabled, no in-app notifications are created for you
- **Email notifications** — when disabled, no emails are sent to you regardless of per-category settings

**Per-category toggles (only apply when email notifications are globally enabled):**
- Borrowing
- Reservations
- Incidents
- Equipment
- Kits
- Consumables
- Projects
- System

Disabling a category suppresses both in-app and email notifications for events in that category. Enabling a category while email notifications are globally off only enables in-app delivery.

---

## 3. Equipment

### 3.1 Browsing and Searching Equipment

Navigate to **Equipment** (`/equipment/`) to see all active, approved equipment.

**Filter options** (top of the page):
- **Search** — matches against name, serial number, model number, manufacturer, and description
- **Category** — dropdown of all categories
- **Location** — dropdown of all locations
- **Status** — Available, Borrowed, Reserved, Under Maintenance, Damaged, Retired
- **Condition** — Excellent, Good, Fair, Poor, Damaged

Results are paginated at 10 per page. Each card shows the equipment name, status badge, condition, category, location, and owner.

> Members see only **Approved** equipment plus any **Pending** equipment they registered themselves. Admins see all equipment including Pending approval items.

### 3.2 Viewing Equipment Details

Click any equipment card or name to open its detail page.

The detail page shows:
- Full description, serial number, model number, manufacturer
- Category, location, owner, current status and condition
- Purchase date and price (if recorded)
- Photo
- **Borrow history** — last 10 borrow requests against this item
- **Lifecycle timeline** — events such as purchase, maintenance, repairs, and status changes
- **Movement log** — history of location changes
- For admins: an **Approve** button if the item is pending approval
- A **Borrow** button if the item is available and you are not already borrowing it
- A **Reserve** button to open a reservation form for this item
- An **Edit** button (visible to the owner and admins)
- A **Log Incident** button (visible to all members)

### 3.3 Registering New Equipment

Any logged-in member can register equipment they own.

1. Go to **Equipment → Add Equipment** (`/equipment/create/`).
2. Fill in:
   - **Name** (required)
   - **Description**
   - **Serial number** (must be unique across all equipment; leave blank if unknown)
   - **Model number**
   - **Manufacturer**
   - **Category** (required) — select existing or create a new one inline
   - **Location** (required) — select existing or create a new one inline
   - **Owner** (required) — defaults to yourself; admins may assign to another user
   - **Status** (defaults to Available)
   - **Condition** (defaults to Good)
   - **Photo** (required when creating; JPEG or PNG, max 20 MB)
   - Purchase date, purchase price, notes (all optional)
3. Click **Add Equipment**.

**Approval:** If you set yourself as the owner, the equipment is **immediately approved** and visible to everyone. If you register equipment and assign a different owner, it enters **Pending Approval** status and is only visible to you and admins until an admin approves it.

A **PURCHASED** lifecycle event is recorded automatically when equipment is created.

### 3.4 Equipment Approval

When a member registers equipment with a different owner, it appears in the Pending Approval queue.

**As an admin:**
1. Open the equipment detail page (the item appears in the equipment list for admins even when Pending).
2. Click **Approve** to make it visible to all members, or **Reject** to decline.

### 3.5 Editing Equipment

Equipment can be edited by its **owner** or any **admin**.

1. Open the equipment detail page.
2. Click **Edit**.
3. Update any fields.
4. Click **Save Changes**.

If the current user is not the owner and not an admin, the edit attempt is redirected back to the detail page with an error message. No changes are saved.

### 3.6 Moving Equipment Between Locations

When equipment moves to a new physical location:

1. Open the equipment detail page.
2. Click **Log Movement**.
3. Select **From Location** (pre-filled with the current location) and **To Location**.
4. Optionally enter a reason.
5. Click **Save**.

A movement record is appended to the movement log and the equipment's location is updated.

### 3.7 Recording Lifecycle Events

A lifecycle event records a significant moment in an equipment item's history.

Event types:
- **Purchased** — added to inventory (auto-created on registration)
- **Deployed** — put into active service
- **Sent to Maintenance** — removed from service for repair
- **Repaired** — returned from repair
- **Damaged** — damage discovered
- **Retired** — permanently taken out of service
- **Status Changed** — any other status transition
- **Condition Changed** — condition update
- **Note** — free-form note

To add an event:
1. Open the equipment detail page.
2. Scroll to **Lifecycle Timeline** and click **Add Event**.
3. Choose the event type and enter a description.
4. Click **Save**.

### 3.8 Deactivating Equipment

Admins can deactivate equipment that should no longer appear in the inventory (retired, lost, or scrapped). Deactivation hides the item from all lists without deleting its history.

This is done from the Django back-office (`/backoffice/`) by setting `is_active = False` on the equipment record.

### 3.9 Categories and Locations

Categories and locations are shared across equipment and consumables.

**Creating a category:**
1. Go to `/equipment/categories/create/`.
2. Enter a name and optional description.
3. Leave **Color** blank for an auto-generated unique color, or pick one.
4. Click **Save**.

**Creating a location:**
1. Go to `/equipment/locations/create/`.
2. Enter a name (e.g., "Cabinet A"), optional building, room, and description.
3. Click **Save**.

Both can also be created inline from the equipment registration form using the "+" button next to the dropdown.

---

## 4. Borrowing

Borrowing allows you to check out a specific piece of equipment or a kit for a defined period.

### 4.1 Submitting a Borrow Request

1. Navigate to **Borrowing → Borrow Equipment** (`/borrowing/create/`), or click **Borrow** on an equipment detail page.
2. Select either **Equipment** or **Kit** (not both).
3. Enter:
   - **Purpose** — describe why you need the item
   - **Due date** — the date you will return it (must be today or a future date)
   - **Project** (optional) — link this borrow to a project
4. Click **Submit Request**.

**Validation rules:**
- The due date cannot be in the past.
- You cannot borrow equipment that has a confirmed reservation overlapping with your due date.

**Auto-approval:** Borrow requests are automatically set to **APPROVED** on submission. There is no separate approval step for single-item borrows. The equipment status is not automatically changed to "Borrowed" at this point — that is a manual status update by the owner if needed.

### 4.2 Borrow Request Status Reference

| Status | Meaning |
|---|---|
| **APPROVED** | Request submitted and approved; item is checked out |
| **ACTIVE** | Item has been physically picked up (manually set by owner or admin) |
| **RETURN_PENDING** | Borrower has submitted the return; awaiting owner confirmation |
| **RETURNED** | Owner confirmed receipt; transaction complete |
| **OVERDUE** | Due date passed without a return being submitted |
| **CANCELLED** | Request was cancelled before pickup |

Status flow:
```
APPROVED → ACTIVE → RETURN_PENDING → RETURNED
                 ↘ OVERDUE (automatic via management command)
```

### 4.3 Viewing Your Active Borrows

Go to **Borrowing** (`/borrowing/`) to see all your borrow requests grouped by status.

Alternatively, the **Member Dashboard** shows your active borrows with their due dates and a visual overdue indicator.

### 4.4 Submitting a Return

When you are done with an item:

1. Open the borrow request detail page (`/borrowing/<id>/`), or click the item from your dashboard.
2. Click **Return Item**.
3. Select the **Return Condition**:
   - Excellent
   - Good
   - Fair
   - Poor
   - Damaged
4. Enter any **notes** (optional but recommended if the condition is not Good).
5. Click **Submit Return**.

The request status becomes **RETURN_PENDING** and the return date is recorded. The equipment owner receives a notification.

### 4.5 Confirming a Return (Equipment Owner)

When someone returns equipment you own, you receive an in-app and email notification.

To confirm:
1. Go to **Borrowing → Return Queue** (`/borrowing/returns/`), or click the notification link.
2. Find the pending return in the **Single Item Returns** section.
3. Click **Confirm Return**.

The borrow status becomes **RETURNED**. The borrower receives a notification.

If you disagree with the condition reported, add a note before confirming. There is no reject-return option — contact the borrower directly if there is a dispute.

### 4.6 Kit Borrow Returns

When a kit is returned, each piece of equipment inside the kit must be confirmed by its individual owner. This is handled through per-item approval records.

**When the borrower submits the return:**
- One `KitItemReturnApproval` record is created for each distinct equipment owner in the kit.
- The kit borrow status becomes **RETURN_PENDING**.
- Each owner receives a notification.

**For each owner:**
1. Go to **Borrowing → Return Queue** (`/borrowing/returns/`).
2. Find your item(s) in the **Kit Item Returns** section.
3. Click **Confirm** next to your item.

The borrow only transitions to **RETURNED** when every owner has confirmed their items. If you confirm your item but another owner has not yet confirmed theirs, the borrow stays **RETURN_PENDING** and the remaining owners see it in their queue.

### 4.7 Overdue Items

An item is overdue when its due date passes while the status is still **APPROVED** or **ACTIVE**.

The system does not detect overdue items in real time — a scheduled management command (`mark_overdue_borrows`) must be run periodically by an administrator. See [Overdue Borrow Detection](#128-overdue-borrow-detection) in the Admin Guide.

When an item is marked overdue:
- Its status changes to **OVERDUE**.
- The borrower receives an in-app and email notification.
- All admins receive an in-app and email notification.

Overdue items appear prominently on the admin dashboard. As a borrower, you should still return the item normally by submitting a return from the borrow detail page.

---

## 5. Reservations

Reservations let you book equipment or a kit for a future time window without immediately checking it out.

### 5.1 Creating a Reservation

1. Navigate to **Reservations → New Reservation** (`/reservations/create/`), or click **Reserve** on an equipment detail page.
2. Select either **Equipment** or **Kit** (not both).
3. Enter:
   - **Start date** — first day of your reservation
   - **End date** — last day of your reservation
   - **Purpose** — describe the planned use
4. Click **Submit**.

The reservation is created with status **PENDING**. The equipment owner receives a notification and must confirm the reservation before it becomes **CONFIRMED**.

> **Note:** Reservations that overlap a confirmed reservation for the same item will be blocked during the borrow request form validation. Check the calendar before creating a reservation to avoid conflicts.

### 5.2 Reservation Status Reference

| Status | Meaning |
|---|---|
| **PENDING** | Submitted; awaiting owner confirmation |
| **CONFIRMED** | Owner confirmed; the period is booked |
| **RETURN_PENDING** | Requester submitted return; awaiting owner confirmation |
| **RETURNED** | Owner confirmed return; complete |
| **CANCELLED** | Cancelled by the requester before the end date |
| **COMPLETED** | Period ended normally (set manually or via future automation) |
| **EXPIRED** | Period passed without any action |

Status flow:
```
PENDING → CONFIRMED → RETURN_PENDING → RETURNED
                    ↘ CANCELLED
```

### 5.3 Viewing Your Reservations

Go to **Reservations** (`/reservations/`) to see all your reservations listed with their status, dates, and item.

### 5.4 Calendar View

The calendar at `/reservations/calendar/` shows all **CONFIRMED** reservations from all members as blocks on a monthly calendar. Use the left/right arrows to navigate between months.

Hovering over a block shows the item name and requester. This view is useful for checking availability before creating a new reservation.

### 5.5 Cancelling a Reservation

You can cancel a reservation that is in **PENDING** or **CONFIRMED** status.

1. Open the reservation detail page.
2. Click **Cancel Reservation**.
3. Confirm the cancellation.

If someone is on the waitlist for the same equipment, the first person in the queue receives an automatic notification.

### 5.6 Submitting a Reservation Return

When the reservation period is over and you have physically returned the item:

1. Open the reservation detail page.
2. Click **Return Item**.
3. Select the **Return Condition** and enter any notes.
4. Click **Submit Return**.

Status becomes **RETURN_PENDING** and the equipment owner is notified.

You can only submit a return when the reservation is in **CONFIRMED** status. If it is already **CANCELLED**, **RETURNED**, or another terminal state, the return button is not shown.

### 5.7 Confirming a Reservation Return (Equipment Owner)

1. Go to **Reservations** (`/reservations/`) and look for items with status **RETURN_PENDING**, or click the notification link.
2. Open the reservation detail page.
3. Click **Confirm Return**.

Status becomes **RETURNED** and the requester is notified.

Only the equipment (or kit) owner can confirm the return. Other members attempting to confirm are redirected with an error.

### 5.8 The Waitlist

If the equipment you need is already reserved or borrowed, you can join the waitlist.

**To join the waitlist:**
1. On the equipment detail page, click **Join Waitlist** (visible when the item is unavailable).
2. Enter optional notes (e.g., when you need it by).
3. Click **Submit**.

You are assigned a position in the queue. Duplicate entries for the same user and item are rejected.

**When you are notified:**
When a confirmed reservation for the item is cancelled, LabTrack automatically notifies the first person in the queue (position 1). After notification, that entry is marked as notified but remains in the list until the user leaves manually.

**To leave the waitlist:**
Open your reservation list, find the waitlist entry, and click **Leave Waitlist**. Your entry is deleted.

---

## 6. Kits

A kit is a named bundle of equipment items that can be borrowed together as a single unit.

### 6.1 Creating a Kit

1. Navigate to **Kits → New Kit** (`/kits/create/`).
2. Enter:
   - **Name** (required)
   - **Description** (optional)
   - **Share with all members** — see [Sharing a Kit](#63-sharing-a-kit)
3. Click **Create Kit**.

The kit is created with no items. You are redirected to the kit detail page.

### 6.2 Adding Items to a Kit

From the kit detail page:

1. Click **Add Item**.
2. Select the **Equipment** from the dropdown.
3. Set the **Quantity** (defaults to 1).
4. Enter optional **Notes** for this item.
5. Click **Add**.

Each item can only appear once per kit. To adjust the quantity, remove the item and re-add it with the correct quantity.

**Removing an item:**
Click the **Remove** button next to the item in the kit detail page.

### 6.3 Sharing a Kit

By default, a kit is private — only you can see and borrow it.

To share:
1. Open the kit detail page.
2. Click **Edit Kit**.
3. Check **Share with all members**.
4. Click **Save**.

Shared kits appear in the **Shared Kits** section of the kit list for all members. Any member can then borrow the shared kit. You retain ownership and must confirm returns.

### 6.4 Borrowing a Kit

Borrowing a kit works the same as borrowing individual equipment:

1. Go to **Borrowing → Borrow Equipment** (`/borrowing/create/`).
2. Leave Equipment blank and select your **Kit**.
3. Fill in purpose and due date.
4. Click **Submit Request**.

Or click **Borrow** from the kit detail page.

The kit borrow is automatically approved. Note that the individual equipment items inside the kit are not locked from simultaneous individual borrows — plan accordingly or use the reservation system for strict scheduling.

### 6.5 Returning a Kit

Returning a kit is described in detail in [Kit Borrow Returns](#46-kit-borrow-returns) in the Borrowing section. Each equipment owner inside the kit must independently confirm their items.

### 6.6 Editing and Deleting Kits

**Edit:** From the kit detail page, click **Edit Kit**. You can change the name, description, and shared status.

**Delete:** From the kit detail page, click **Delete Kit**. This permanently removes the kit and all its item records. Existing borrow requests linked to the kit are preserved (the kit field becomes null). Only the kit creator or an admin can delete a kit.

---

## 7. Consumables

Consumables are non-returnable supplies (chemicals, components, materials) with quantity tracking.

### 7.1 Browsing Consumables

Navigate to **Consumables** (`/consumables/`) to see all active consumables. The list shows name, current quantity, unit, and a low-stock badge for items at or below their threshold.

Click a consumable to view its detail page, which includes:
- Full description, category, location, supplier, unit cost
- Current quantity and threshold
- Usage log (all recorded consumption events)

### 7.2 Logging Consumable Usage

Any logged-in member can record that they used a consumable.

1. Open the consumable detail page.
2. Click **Log Usage**.
3. Enter:
   - **Quantity used** — must not exceed the current stock
   - **Purpose** — brief description of the use
   - **Project** (optional) — link the usage to a project
4. Click **Log Usage**.

The stock is reduced immediately. If you enter a quantity greater than the available stock, the form is rejected and the stock is unchanged.

### 7.3 Adding a New Consumable (Admin)

1. Go to **Consumables → Add Consumable** (`/consumables/create/`).
2. Fill in:
   - **Name** (required)
   - **Description**
   - **Category** (optional)
   - **Location** (optional)
   - **Quantity** — initial stock level
   - **Unit** — Piece, Box, Pack, Bottle, Liter, Gram, Meter, Roll, or Other
   - **Low stock threshold** — quantity at or below which the item appears as low stock
   - **Unit cost** (optional)
   - **Supplier** (optional)
   - **Notes** (optional)
3. Click **Add Consumable**.

### 7.4 Restocking a Consumable (Admin)

When new stock arrives:

1. Open the consumable detail page.
2. Click **Restock**.
3. Enter:
   - **Quantity to add** — added on top of current stock
   - **Notes** — e.g., "New delivery from supplier X"
4. Click **Restock**.

The stock is increased immediately.

### 7.5 Low-Stock List (Admin)

Navigate to **Consumables → Low Stock** (`/consumables/low-stock/`) to see every consumable where `quantity ≤ low_stock_threshold`. Use this list to prioritize reordering.

The admin dashboard also shows a **Low Stock** alert card when any consumable is at or below its threshold.

---

## 8. Incidents

The incidents module tracks equipment damage, safety issues, and operational faults through a resolution workflow.

### 8.1 Reporting an Incident

Any member who discovers a problem with equipment should report it immediately.

1. Navigate to **Incidents → Report Incident** (`/incidents/create/`), or click **Log Incident** on the equipment detail page.
2. Fill in:
   - **Equipment** (required) — the affected item
   - **Title** (required) — short summary, e.g., "Screen cracked"
   - **Description** (required) — detailed description of the issue
   - **Severity**:
     - **Low** — minor cosmetic or non-blocking issue
     - **Medium** — affects usability but not safety
     - **High** — significant impairment or safety concern
     - **Critical** — immediate safety risk or complete failure
   - **Photo** (optional) — attach an image of the damage
3. Click **Report Incident**.

The incident is created with status **Open** and you are recorded as the reporter. The equipment owner receives a notification.

### 8.2 Incident Status Reference

| Status | Meaning |
|---|---|
| **Open** | Reported; no investigator assigned yet |
| **Investigating** | Assigned to an investigator; work in progress |
| **Resolved** | Issue addressed; awaiting closure review |
| **Closed** | Fully closed; no further action needed |

Status flow:
```
Open → Investigating → Resolved → Closed
```

### 8.3 Assigning an Investigator

The reporter, the equipment owner, or an admin can assign an investigator.

1. Open the incident detail page.
2. Click **Assign Investigator**.
3. Select a user from the dropdown.
4. Click **Assign**.

The status changes to **Investigating** and the assignee receives a notification.

### 8.4 Resolving an Incident

The assignee or an admin marks the incident resolved when the issue has been addressed.

1. Open the incident detail page.
2. Click **Mark Resolved**.
3. Enter a **Resolution** description — describe what was done to fix the issue.
4. Click **Resolve**.

Status changes to **Resolved**. The reporter receives a notification.

### 8.5 Closing an Incident

After the resolution has been reviewed and accepted:

1. Open the incident detail page.
2. Click **Close Incident**.

Status becomes **Closed**. Closed incidents remain in the list for historical reference but cannot be re-opened.

### 8.6 Maintenance Logs

Maintenance records track scheduled or completed servicing of equipment.

**To add a maintenance log:**
1. Open the equipment detail page.
2. Click **Log Maintenance**.
3. Fill in:
   - **Maintenance type**: Preventive, Corrective, Inspection, or Calibration
   - **Status**: Scheduled, In Progress, Completed, or Cancelled
   - **Performed by** — the person doing or overseeing the work
   - **Description** — what needs to be or was done
   - **Scheduled date** — planned date
   - **Completed date** (optional) — actual completion date
   - **Cost** (optional)
   - **Notes** (optional)
4. Click **Save**.

Maintenance logs are visible on the equipment detail page under **Maintenance History**.

### 8.7 Calibration Logs

Calibration logs track precision checks for measurement equipment.

**To add a calibration log:**
1. Open the equipment detail page.
2. Click **Log Calibration**.
3. Fill in:
   - **Calibrated by**
   - **Calibration date**
   - **Next calibration date** (optional) — for scheduling recurring checks
   - **Status**: Pass, Fail, or Pending
   - **Certificate number** (optional)
   - **Notes** (optional)
4. Click **Save**.

---

## 9. Projects

Projects provide lightweight coordination for lab work that involves multiple members and equipment.

### 9.1 Creating a Project

1. Navigate to **Projects → New Project** (`/projects/create/`).
2. Fill in:
   - **Name** (required)
   - **Description** (optional)
   - **Status** (defaults to Active)
   - **Start date** (optional)
   - **End date** (optional)
3. Click **Create Project**.

You are automatically set as the project **Lead**.

### 9.2 Managing Project Members

The project lead or an admin can add and remove members.

**Adding a member:**
1. Open the project detail page.
2. Click **Add Member**.
3. Select a user and a role: Lead, Member, or Observer.
4. Click **Add**.

**Roles within a project:**
- **Lead** — full control; can manage members and update the project
- **Member** — can view the project and is listed as a participant
- **Observer** — read-only participant

**Removing a member:**
Click the **Remove** button next to a member on the project detail page.

### 9.3 Updating Project Status

The project lead or an admin can change the project status at any time.

1. Open the project detail page.
2. Click **Edit Project**.
3. Change **Status** to Active, On Hold, Completed, or Cancelled.
4. Click **Save**.

---

## 10. Notifications

### 10.1 In-App Notifications

The **notification bell** in the top bar shows a badge with the count of unread notifications.

Click the bell (or navigate to `/notifications/`) to open your notification inbox.

Each notification shows:
- A description of the event
- The time it was created (relative, e.g., "3 hours ago")
- A link to the related object (e.g., the borrow request, incident, or reservation)
- A read / unread indicator

**Marking notifications as read:**
- Click a notification to open the linked page — the notification is marked read automatically.
- Click **Mark All Read** to clear all unread indicators at once.

### 10.2 Email Notifications

When SMTP is configured, every in-app notification also triggers an email to the recipient's registered email address, provided:
1. The user has **Email Notifications** globally enabled in their profile.
2. The user has the **per-category toggle** enabled for that event type.

Email links use the absolute `SITE_URL` configured in the server environment so they work correctly from any email client.

### 10.3 Notification Events Reference

| Event | Who is notified |
|---|---|
| New borrow request submitted | All admins |
| Borrow approved | Borrower |
| Borrow rejected | Borrower |
| Borrow overdue | Borrower + all admins |
| Return submitted (single item) | Equipment owner |
| Return confirmed (single item) | Borrower |
| Kit item return submitted | Each equipment owner in the kit |
| Kit item confirmed (all done) | Borrower |
| Reservation created (pending) | Equipment / kit owner |
| Reservation confirmed | Requester |
| Reservation cancelled | Requester; next person on waitlist (if any) |
| Reservation return submitted | Equipment / kit owner |
| Reservation return confirmed | Requester |
| Incident reported | Equipment owner |
| Incident assigned to you | Assignee |
| Incident resolved | Reporter |
| Incident status updated | Reporter |

---

## 11. Activity Log

The activity log at `/activity/` is an immutable audit trail of every significant action performed in LabTrack.

Each entry records:
- **Actor** — the user who performed the action
- **Action type** — e.g., CREATE, UPDATE, STATUS_CHANGE, LOGIN, LOGOUT
- **Description** — human-readable summary of what happened
- **Timestamp** — exact date and time

The activity log is accessible to **admins only**. It is read-only — entries cannot be edited or deleted.

Use the activity log to:
- Investigate who changed a piece of equipment's status
- Audit borrow and return transactions
- Track user logins and logouts
- Identify who filed or resolved an incident

---

## 12. Admin Guide

### 12.1 First-Time Setup

After deploying LabTrack for the first time:

1. Run `python manage.py createsuperuser` (or `docker compose exec web python manage.py createsuperuser`) and create an account with your email and a strong password.
2. Log in to LabTrack.
3. Go to **Members** (`/accounts/members/`) and confirm your account shows the **Admin** role (superusers are automatically Admin).
4. Create **Categories** at `/equipment/categories/create/` (e.g., "Electronics", "Measurement", "Safety").
5. Create **Locations** at `/equipment/locations/create/` (e.g., "Lab A", "Storage Cabinet 1").
6. Register your first equipment items.
7. If email notifications are needed, configure SMTP in `.env` and restart the server.

### 12.2 Managing Members

Go to **Members** (`/accounts/members/`) to see all registered users.

The list shows each user's username, email, role, and join date. Click a user to view their full profile, including their borrow history, reservations, and notification preferences.

**Deactivating a user:**
From the Django back-office (`/backoffice/accounts/customuser/`), find the user and uncheck **Active**. Deactivated users cannot log in. Their existing records are preserved.

### 12.3 Assigning Roles

1. Go to **Members** (`/accounts/members/`).
2. Click the user's name to open their profile.
3. Click **Change Role** (admins only).
4. Select **Admin** or **Member**.
5. Click **Save**.

> Users with no role assigned cannot access any module. Always assign a role to newly registered users.

### 12.4 Admin Dashboard

The admin dashboard at `/dashboard/` provides a real-time overview:

- **Stats bar:** total active equipment, active borrows, pending returns, low-stock consumables, open incidents
- **Overdue Borrows** alert card — click to view the borrow list filtered by status OVERDUE
- **Low Stock Consumables** alert card — click to go to `/consumables/low-stock/`
- **Quick actions:** common navigation shortcuts
- **Equipment by status** chart — doughnut chart of current distribution
- **Monthly borrow activity** chart — bar chart of the last 6 months
- **Recent Members** — last 5 accounts created

### 12.5 Admin Panel

The admin panel at `/admin/` is a management hub distinct from the Django back-office.

It shows:
- **Counts** for every module (users, equipment, borrows, reservations, kits, consumables, incidents, projects, notifications, and activity events)
- Navigation links to all management areas
- Recent activity feed

### 12.6 Approving Pending Equipment

When a member registers equipment with a different owner it enters the **Pending Approval** queue.

1. Open the equipment detail page for the pending item (visible to admins in the equipment list).
2. The page shows an **Approve** button in the top action area.
3. Click **Approve**.

The item is immediately visible to all members. The registering member receives a notification.

To reject instead:
1. Go to the equipment detail page.
2. Click **Reject** (sets `approval_status = REJECTED` and hides the item).

### 12.7 Return Queue

The return queue at `/borrowing/returns/` shows all borrow requests awaiting your confirmation as equipment owner. It is split into two sections:

**Single Item Returns** — a borrow of individual equipment where you are the owner. Click **Confirm Return** to close the transaction.

**Kit Item Returns** — individual equipment items inside kit borrows that you own. Each row shows the kit name, borrower, and reported condition. Click **Confirm** to mark your specific items as returned. When all owners in the kit have confirmed, the overall borrow status becomes **RETURNED**.

### 12.8 Overdue Borrow Detection

Overdue detection is not automatic in real time — it runs via a management command that should be scheduled to run once per day.

**Running manually:**
```bash
python manage.py mark_overdue_borrows --dry-run   # preview, no changes
python manage.py mark_overdue_borrows             # apply
```

**With Docker:**
```bash
docker compose exec web python manage.py mark_overdue_borrows
```

**Scheduling on Linux / Raspberry Pi (cron):**
```cron
0 1 * * * cd /path/to/LabTrack && python manage.py mark_overdue_borrows >> /var/log/labtrack-overdue.log 2>&1
```

**Scheduling on Windows (Task Scheduler):**

1. Open **Task Scheduler**.
2. Click **Create Basic Task**.
3. Name it "LabTrack Overdue Check".
4. Set the trigger to **Daily** at 01:00.
5. Set the action to **Start a program**: `python` with arguments `manage.py mark_overdue_borrows` and start in the LabTrack directory.

When the command runs, every borrow with a past due date that is still **APPROVED** or **ACTIVE** is transitioned to **OVERDUE**, and notifications are sent to the borrower and all admins.

### 12.9 Django Back-Office

The Django back-office is available at `/backoffice/` (not `/admin/` — that path is the LabTrack admin panel described above).

Use the back-office for:
- Direct inspection and editing of any database record
- Bulk actions (e.g., deactivating multiple users at once)
- Recovery operations (e.g., fixing a corrupted status)
- Creating records that do not yet have a front-end form

Access is restricted to superusers (accounts created with `createsuperuser` or manually set `is_staff=True` and `is_superuser=True` in the database).

> The back-office bypasses all application-level validation and signals. Use it carefully. Any status change made through the back-office does not fire notifications or activity log entries unless triggered via the Django admin's `save_model` hook.
