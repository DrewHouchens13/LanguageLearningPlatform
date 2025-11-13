# Administrator Guide

This guide explains how to access and use the Django admin interface to manage users and their progress.

## Table of Contents
1. [Creating Your First Admin Account](#creating-your-first-admin-account)
2. [Accessing the Admin Interface](#accessing-the-admin-interface)
3. [Managing Users](#managing-users)
4. [Managing Lessons](#managing-lessons)
5. [Managing Daily Quests](#managing-daily-quests)
6. [Managing User Progress](#managing-user-progress)
7. [Admin Actions Reference](#admin-actions-reference)

---

## Creating Your First Admin Account

### On Production (Render.com)

To create an admin account on your production site:

1. Go to the [Render Dashboard](https://dashboard.render.com/)
2. Select your Language Learning Platform service
3. Click on the **Shell** tab
4. Run the following command:
   ```bash
   python manage.py createsuperuser
   ```
5. Follow the prompts to enter:
   - Username (e.g., `admin`)
   - Email address
   - Password (enter twice for confirmation)

### On Local Development

If you're running the app locally:

1. Ensure your virtual environment is activated
2. Run:
   ```bash
   python manage.py createsuperuser
   ```
3. Follow the prompts to create your admin account

---

## Accessing the Admin Interface

### Production
Navigate to: `https://language-learning-platform-xb6f.onrender.com/admin/`

### Local Development
Navigate to: `http://localhost:8000/admin/`

**Login** with your superuser credentials.

---

## Managing Users

### Viewing All Users

1. Click on **Users** in the admin home page
2. You'll see a list of all registered users with:
   - Username
   - Email
   - First name & Last name
   - Staff status
   - Superuser status
   - Date joined
   - Last login

### Searching Users

Use the search box at the top to find users by:
- Username
- Email
- First name
- Last name

### Filtering Users

Use the filter sidebar to filter by:
- Staff status
- Superuser status
- Active status
- Date joined

### Viewing Individual User Details

1. Click on any username to view/edit user details
2. You'll see several sections:
   - **Personal info**: Username, names, email
   - **Permissions**: Staff status, superuser status, active status
   - **Important dates**: Last login, date joined
   - **Progress Information**: Collapsible section showing user's learning stats

### Editing User Information

You can edit:
- Username
- First name, Last name
- Email address
- Active status
- Staff status (makes user able to access admin)
- Superuser status (gives full admin permissions)
- Specific permissions (granular control)

**Click "Save" to apply changes.**

---

## Admin Actions (Bulk Operations)

Admin actions allow you to perform operations on multiple users at once.

### How to Use Admin Actions

1. Navigate to the **Users** list
2. **Check the boxes** next to the users you want to modify
3. Select an action from the **Action** dropdown at the top
4. Click **Go**
5. Confirm the action

### Available Actions

#### 1. Reset Password to 'password123'

**What it does**: Resets selected users' passwords to the default password `password123`

**Use case**: When users forget their passwords or need a password reset

**Steps**:
1. Select user(s)
2. Choose "Reset password to 'password123'" from Actions
3. Click Go
4. Users can now log in with `password123`

⚠️ **Important**: Inform users to change their password after logging in with the default password.

#### 2. Make Selected Users Administrators

**What it does**: Grants both `is_staff` and `is_superuser` permissions to selected users

**Use case**: Promoting users to administrators

**Steps**:
1. Select user(s)
2. Choose "Make selected users administrators"
3. Click Go
4. Users now have full admin access

#### 3. Remove Admin Privileges

**What it does**: Removes `is_staff` and `is_superuser` permissions from selected users

**Use case**: Demoting administrators back to regular users

**Steps**:
1. Select user(s)
2. Choose "Remove admin privileges"
3. Click Go
4. Users no longer have admin access

#### 4. Reset All User Progress

**What it does**:
- Deletes all lesson completions for selected users
- Deletes all quiz results for selected users
- Resets UserProgress statistics to zero

**Use case**: Starting a user's progress from scratch

**Steps**:
1. Select user(s)
2. Choose "Reset all user progress"
3. Click Go

⚠️ **Warning**: This action **permanently deletes** all progress data. Cannot be undone.

---

## Managing Lessons

The admin interface provides tools to create and manage lessons, flashcards, and quiz questions.

### Viewing Lessons

1. Click **Lessons** in the admin home page
2. View all lessons with:
   - Title and slug
   - Lesson type (flashcard or quiz)
   - XP value
   - Category
   - Publication status
   - Order

### Creating a Lesson

1. Click **Add Lesson** button
2. Fill in required fields:
   - **Title**: Name of the lesson (e.g., "Colors", "Numbers")
   - **Slug**: URL-friendly identifier (auto-generated from title)
   - **Lesson Type**: Choose "flashcard" or "quiz"
   - **XP Value**: Experience points awarded (default: 100)
   - **Category**: Learning category (e.g., "Vocabulary", "Grammar")
   - **Is Published**: Check to make lesson visible to users
   - **Order**: Display order in lesson list
3. Click **Save**

### Adding Content to Lessons

#### For Flashcard Lessons:
1. Open the lesson in admin
2. Scroll to **Flashcards** section
3. Click **Add another Flashcard**
4. Fill in:
   - Front text (e.g., "Red")
   - Back text (e.g., "Rojo")
   - Order (determines display sequence)
   - Optional: Image URL, Audio URL
5. Repeat for all flashcards (minimum 5 recommended)
6. Click **Save**

#### For Quiz Lessons:
1. Open the lesson in admin
2. Scroll to **Quiz Questions** section
3. Click **Add another Quiz Question**
4. Fill in:
   - Question text
   - Options (JSON array: `["Option 1", "Option 2", "Option 3", "Option 4"]`)
   - Correct index (0-3, indicating which option is correct)
   - Explanation (optional feedback text)
   - Order
5. Repeat for all questions (minimum 5 recommended)
6. Click **Save**

### Bulk Actions for Lessons

- **Publish selected lessons**: Make multiple lessons visible to users
- **Unpublish selected lessons**: Hide lessons from users
- **Delete selected lessons**: Permanently remove lessons

---

## Managing Daily Quests

Daily quests are automatically generated each day. Admins can view and manage quest data.

### How Daily Quests Work

The system automatically generates two quests per day at midnight:

1. **Time-Based Quest**: "Study for 15 Minutes" - 50 XP
2. **Lesson-Based Quest**: "Complete [Random Lesson]" - Varies by lesson

### Viewing Daily Quests

1. Click **Daily Quests** in the admin home page
2. View all quests with:
   - Date
   - Title
   - Quest type (study or quiz)
   - Based on lesson
   - XP reward
   - Number of user attempts

### Quest Generation

Quests are generated automatically by the `DailyQuestService`:
- Runs daily at midnight
- Selects a random published lesson for lesson-based quest
- Creates both quest types for the day
- Reuses existing quests if already generated for that date

### Managing Quest Attempts

1. Click **User Daily Quest Attempts** in admin
2. View user progress on quests:
   - User
   - Daily quest
   - Completion status
   - Correct answers / Total questions
   - XP earned
   - Completion timestamp
3. Filter by user, quest, or completion status

### Quest History

Administrators can:
- View total quests completed by users
- Check XP earned from quests
- Identify most popular quest types
- Monitor daily engagement

**Note**: The daily quest system is fully automated. Manual quest creation is not required.

---

## Managing User Progress

### Viewing User Progress Records

1. From admin home, click **User Progress**
2. View all user progress records with stats:
   - Total minutes studied
   - Total lessons completed
   - Total quizzes taken
   - Quiz accuracy percentage
   - Last updated timestamp

### Filtering Progress

Filter by:
- Created date
- Updated date

### Editing Progress Manually

1. Click on a user's progress record
2. You can manually modify:
   - Total minutes studied
   - Total lessons completed
   - Total quizzes taken
   - Overall quiz accuracy
3. Click **Save**

### Progress Actions

#### Reset Progress Statistics

**What it does**: Resets the statistics in UserProgress to zero (but doesn't delete lesson/quiz records)

**Steps**:
1. Select UserProgress record(s)
2. Choose "Reset progress statistics"
3. Click Go

---

## Managing Lesson Completions

### Viewing Lesson Completions

1. Click **Lesson Completions**
2. View all completed lessons with:
   - User
   - Lesson title/ID
   - Duration in minutes
   - Completion date

### Searching Lessons

Search by:
- Username
- Lesson title
- Lesson ID

### Deleting Lesson Completions

**Individual deletion**:
1. Click on a lesson completion
2. Click "Delete" at the bottom
3. Confirm deletion

**Bulk deletion**:
1. Select multiple lesson completions
2. Choose "Delete selected lesson completions" from Actions
3. Click Go

---

## Managing Quiz Results

### Viewing Quiz Results

1. Click **Quiz Results**
2. View all quiz attempts with:
   - User
   - Quiz title/ID
   - Score / Total questions
   - Accuracy percentage
   - Completion date

### Searching Quiz Results

Search by:
- Username
- Quiz title
- Quiz ID

### Deleting Quiz Results

**Individual deletion**:
1. Click on a quiz result
2. Click "Delete" at the bottom
3. Confirm deletion

**Bulk deletion**:
1. Select multiple quiz results
2. Choose "Delete selected quiz results" from Actions
3. Click Go

---

## Security Best Practices

1. **Change Default Password**: If you reset a user's password to `password123`, ensure they change it upon login
2. **Limit Superuser Access**: Only grant superuser status to trusted administrators
3. **Regular Audits**: Periodically review admin user list to ensure only authorized users have admin access
4. **Use Strong Passwords**: Ensure admin accounts use strong, unique passwords
5. **Monitor Changes**: Review admin log entries to track what changes were made and by whom

---

## Common Tasks Quick Reference

| Task | Steps |
|------|-------|
| Create admin account (production) | Render Dashboard → Shell → `python manage.py createsuperuser` |
| Create admin account (local) | Terminal → `python manage.py createsuperuser` |
| Access admin panel | Navigate to `/admin/` |
| Reset user password | Users → Select user(s) → Action: "Reset password to 'password123'" |
| Make user admin | Users → Select user(s) → Action: "Make selected users administrators" |
| Remove admin access | Users → Select user(s) → Action: "Remove admin privileges" |
| Reset user progress | Users → Select user(s) → Action: "Reset all user progress" |
| View user's progress | Click on username → Scroll to "Progress Information" section |
| Delete lesson completion | Lesson Completions → Select → Action: "Delete selected lesson completions" |
| Delete quiz result | Quiz Results → Select → Action: "Delete selected quiz results" |

---

## Troubleshooting

### Can't Access Admin Panel

**Problem**: Getting 302 redirect or "not authorized" error

**Solution**:
- Ensure your user has `is_staff=True` and `is_superuser=True`
- Check you're using the correct credentials
- Clear browser cache and cookies

### Changes Not Saving

**Problem**: Changes to user data aren't persisting

**Solution**:
- Ensure you clicked the "Save" button
- Check for validation errors at the top of the form
- Verify database connectivity (check Render logs)

### Can't Create Superuser on Render

**Problem**: `createsuperuser` command fails

**Solution**:
- Ensure database migrations have run: `python manage.py migrate`
- Check database environment variables are set correctly
- Try using Render's web shell instead of SSH

---

## Support

For technical issues or questions:
- Check the main [README.md](README.md) for general setup
- Review [CLAUDE.md](CLAUDE.md) for development details
- Check Render logs for production errors

---

**Last Updated**: October 2025
