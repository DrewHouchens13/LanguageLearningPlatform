# Language Learning Platform - User Guide

Welcome to the Language Learning Platform! This guide will help you get started and make the most of your language learning journey.

## Table of Contents

- [Getting Started](#getting-started)
- [Creating an Account](#creating-an-account)
- [Taking the Placement Test](#taking-the-placement-test)
- [Logging In](#logging-in)
- [Managing Your Account](#managing-your-account)
- [Password & Username Recovery](#password--username-recovery)
- [Using the Dashboard](#using-the-dashboard)
- [Learning with Lessons](#learning-with-lessons)
- [Daily Quests](#daily-quests)
- [XP and Leveling System](#xp-and-leveling-system)
- [Tracking Your Progress](#tracking-your-progress)
- [Security & Privacy](#security--privacy)
- [Troubleshooting](#troubleshooting)
- [Getting Help](#getting-help)

---

## Getting Started

The Language Learning Platform helps you track your language learning progress, complete lessons, and monitor your achievements.

### System Requirements

- Modern web browser (Chrome, Firefox, Safari, or Edge)
- Internet connection
- JavaScript enabled

### Accessing the Platform

**Production:** https://language-learning-platform-xb6f.onrender.com
**Local Development:** http://localhost:8000

---

## Creating an Account

1. **Navigate to the platform** in your web browser
2. **Click "Sign Up"** or **"Create Account"** button
3. **Fill in the registration form:**
   - Full Name
   - Email Address (must be valid - you'll use this to log in)
   - Password (minimum 8 characters)
   - Confirm Password
4. **Check "I agree to Terms of Service"**
5. **Click "Create Account"**

### Password Requirements

Your password must:
- Be at least 8 characters long
- Not be too common (e.g., "password123" is not allowed)
- Not be entirely numeric
- Not be too similar to your email or name

### After Registration

You'll be automatically logged in and redirected to the landing page. Your username is automatically generated from your email address.

**Important:** After creating your account, we recommend taking the placement test to personalize your learning experience!

---

## Taking the Placement Test

The placement test (onboarding assessment) helps us understand your current language level and customize your learning path.

### How to Take the Test

1. **Navigate to "Placement Test"** from the navigation menu or dashboard
2. **Read the welcome instructions** explaining the test format
3. **Click "Start Assessment"** when ready
4. **Answer 5 questions** testing your Spanish knowledge
5. **Submit your answers** when complete
6. **View your results** including:
   - Score and proficiency level (Beginner, Intermediate, or Advanced)
   - Personalized feedback
   - Recommended next steps

### Test Features

- **Multiple Choice Format:** Each question has 4 possible answers
- **Immediate Feedback:** See your results instantly after submission
- **Proficiency Levels:**
  - **Beginner** (0-60%): Start with fundamental concepts
  - **Intermediate** (60-80%): Build on existing knowledge
  - **Advanced** (80-100%): Challenge yourself with complex material
- **Retake Anytime:** You can retake the test to update your level

### After the Test

Based on your results, you'll receive:
- A proficiency level badge
- Personalized lesson recommendations
- Access to appropriate difficulty content

---

## Logging In

1. **Go to the login page**
2. **Enter your username or email address**
3. **Enter your password**
4. **Optional:** Check "Remember me" to stay logged in
5. **Click "Login"**

### Forgot Your Password or Username?

See the [Password & Username Recovery](#password--username-recovery) section below.

---

## Managing Your Account

After logging in, you can manage your account settings by clicking the **"Account"** button in the navigation bar (located to the left of the "Logout" button).

### Updating Your Email Address

1. Click **"Account"** in the navigation
2. Scroll to **"Update Email Address"** section
3. Enter your **new email address**
4. Enter your **current password** (for verification)
5. Click **"Update Email"**
6. You'll see a success message if the update was successful

**Note:** Your current password is required to change your email for security reasons.

#### Possible Errors:
- "Current password is incorrect" - Check your password and try again
- "Please enter a valid email address" - Ensure email format is correct
- "This email is already in use" - Another account is using this email

---

### Updating Your Name

1. Click **"Account"** in the navigation
2. Scroll to **"Update Name"** section
3. Enter your **First Name** (required)
4. Enter your **Last Name** (optional)
5. Click **"Update Name"**

Your name will be displayed in your dashboard and profile.

---

### Updating Your Username

1. Click **"Account"** in the navigation
2. Scroll to **"Update Username"** section
3. Enter your **new username**
4. Click **"Update Username"**

**Important:**
- Your username must be unique
- You can log in with either your username or email address
- Your username is visible to other users

#### Possible Errors:
- "This username is already taken" - Choose a different username
- "Username cannot be empty" - Enter a valid username

---

### Changing Your Password

1. Click **"Account"** in the navigation
2. Scroll to **"Change Password"** section
3. Enter your **current password**
4. Enter your **new password**
5. **Confirm your new password** (must match)
6. Click **"Change Password"**

**Security Notes:**
- You'll remain logged in after changing your password
- Your current password is required
- New password must meet security requirements

#### Possible Errors:
- "Current password is incorrect" - Verify your current password
- "New passwords do not match" - Re-enter both password fields
- "This password is too short" - Use at least 8 characters
- "This password is too common" - Choose a more unique password

---

### Updating Your Profile Picture (Avatar)

1. Click **"Account"** in the navigation
2. Scroll to **"Update Profile Picture"** section
3. View your current avatar (either custom upload or Gravatar)
4. Click **"Choose Image"** to select a new avatar
5. Select a PNG or JPG image file (max 5MB)
6. Click **"Upload Avatar"**

**Avatar Features:**
- **Gravatar Integration:** If you don't upload a custom avatar, your profile will automatically use your Gravatar (based on your email address)
- **Automatic Resize:** Uploaded images are automatically resized to 200x200 pixels
- **Format Conversion:** RGBA images are converted to RGB for JPEG compatibility
- **File Requirements:**
  - Accepted formats: PNG, JPG/JPEG
  - Maximum file size: 5MB
  - Recommended size: 200x200 pixels or larger

**Where Your Avatar Appears:**
- Navigation bar (small 32px circular icon)
- Account page (80px display)
- Progress page (120px header)
- Dashboard (200px hero image)

#### Possible Errors:
- "Invalid file type" - Use PNG or JPG images only
- "File size too large" - Reduce file size to under 5MB
- If upload fails, check your internet connection and try again

**Gravatar Setup (Optional):**
If you want a custom Gravatar without uploading:
1. Visit [gravatar.com](https://gravatar.com)
2. Create an account with your platform email address
3. Upload an avatar on Gravatar
4. Your avatar will automatically appear on the platform

---

## Password & Username Recovery

### Forgot Your Password?

1. **Go to the login page**
2. **Click "Forgot Password?"** link
3. **Enter your email address**
4. **Click "Send Reset Link"**
5. **View the simulated email** displayed on the page
   - For this college project, password reset emails are displayed directly on the page in a styled box
   - No actual email is sent (SMTP not required)
   - **Look for the blue gradient box** showing the simulated email
6. **Click the reset link** shown in the simulated email
7. **Enter your new password** (twice)
8. **Click "Reset Password"**
9. You'll be automatically logged in

**Important:**
- Password reset links expire after **20 minutes** for security
- If your link expires, request a new one
- For security, you'll see a success message even if the email doesn't exist
- The simulated email is for demonstration purposes (college project feature)

### Forgot Your Username?

1. **Go to the login page**
2. **Click "Forgot Username?"** link
3. **Enter your email address**
4. **Click "Send Username"**
5. **View the simulated email** displayed on the page
   - For this college project, username reminder emails are displayed directly on the page in a styled box
   - No actual email is sent (SMTP not required)
   - **Look for the blue gradient box** showing the simulated email with your username

**Note:** You can log in with either your username or email address, so if you know your email, you can skip this step and log in directly with your email.

---

## Using the Dashboard

After logging in, access your dashboard by clicking **"Dashboard"** in the navigation.

### Dashboard Features

Your dashboard shows:
- **Profile Section:** Your avatar, name, and member-since date
- **XP and Level:** Current level, total XP, and progress to next level
- **Streak Counter:** Days of consecutive learning activity
- **Daily Quests:** Two quests refreshed daily
  - Time-based quest: Study for 15 minutes
  - Lesson-based quest: Complete a specific lesson
- **Recommended Lessons:** Personalized lesson suggestions
- **Recent Activity:** Your latest completed lessons and achievements

---

## Learning with Lessons

Access interactive lessons by clicking **"Lessons"** in the navigation menu.

### Lesson Types

The platform offers two types of lessons:

#### 1. **Flashcard Lessons**
- Learn vocabulary through interactive flashcards
- Click to flip cards and reveal translations
- Navigate through cards at your own pace
- Take a quiz to test your memory
- **Example:** Colors, Numbers, Common Phrases

#### 2. **Quiz Lessons**
- Answer multiple-choice questions
- Receive immediate feedback on your answers
- Review correct answers after submission
- Track your accuracy and improvement
- **Example:** Grammar, Verb Conjugation, Comprehension

### Taking a Lesson

1. **Browse Lessons** from the lessons page
2. **Click on a lesson** to view details
3. **Start the Lesson:**
   - For flashcards: Study the cards, then click "Take Quiz"
   - For quizzes: Click "Start Quiz" to begin
4. **Complete the Quiz:** Answer all questions
5. **Submit Your Answers** when finished
6. **View Results:**
   - Score and percentage
   - XP earned
   - Correct/incorrect answers review
   - Option to retry

### Lesson Features

- **Progress Tracking:** See which lessons you've completed
- **XP Rewards:** Earn experience points for each completed lesson
- **Difficulty Levels:** Lessons are categorized by proficiency level
- **Immediate Feedback:** Know your score right away
- **Review Mode:** Go back to review lesson content anytime

---

## Daily Quests

Complete daily quests to earn bonus XP and maintain your learning streak!

### Quest Types

Every day at midnight, two new quests are generated:

#### 1. **Time-Based Quest** (⏱️ Study for 15 Minutes)
- **Goal:** Accumulate 15 minutes of study time
- **Reward:** 50 XP
- **How it Works:**
  - Complete any lesson quizzes throughout the day
  - Time is automatically tracked
  - Progress bar shows your current time
- **Completion:** Automatically completes when you reach 15 minutes

#### 2. **Lesson-Based Quest** (📚 Complete Specific Lesson)
- **Goal:** Complete the assigned lesson
- **Reward:** Same XP as the lesson (typically 100-150 XP)
- **How it Works:**
  - A random published lesson is assigned
  - Click "Go to [Lesson Name]" to start
  - Complete the lesson quiz
- **Completion:** Automatically completes when you finish the assigned lesson

### Accessing Daily Quests

1. Click **"Daily Quests"** in the dashboard
2. View both quest cards showing:
   - Quest title and description
   - Progress indicator
   - XP reward
   - Completion status
3. Click the action button to start working on a quest

### Quest Features

- **Daily Refresh:** New quests every day at midnight
- **Automatic Completion:** Quests complete automatically when goals are met
- **Quest History:** View past completed quests and total XP earned
- **Streak Bonus:** Completing quests daily helps maintain your learning streak
- **Both Completable:** You can complete both quests in one day for maximum XP!

### Quest History

Click **"Quest History"** to view:
- All completed quests
- Completion dates
- XP earned from each quest
- Total quest XP across all time
- Performance statistics

---

## XP and Leveling System

Track your progress and unlock achievements through our XP (Experience Points) and leveling system.

### Earning XP

You can earn XP in multiple ways:

| Activity | XP Earned |
|----------|-----------|
| Complete a Flashcard Lesson | 100 XP |
| Complete a Quiz Lesson | 150 XP |
| Complete Time-Based Daily Quest | 50 XP |
| Complete Lesson-Based Daily Quest | 100-150 XP (same as lesson) |

### Level System

- **Starting Level:** Level 1 (0 XP)
- **Level Progression:** XP required increases with each level
- **Current Level Display:** Visible on dashboard and progress page
- **Level Badges:** Visual indicators of your current level

### XP Calculation Formula

XP required for next level = `100 × current_level`

**Example:**
- Level 1 → Level 2: 100 XP needed
- Level 2 → Level 3: 200 XP needed
- Level 5 → Level 6: 500 XP needed

### Tracking Your XP

View your XP progress on:
- **Dashboard:** Large circular progress indicator
- **Progress Page:** Detailed XP statistics
- **Navigation Bar:** Current level display (for quick reference)

### Benefits of Leveling Up

- 🏆 **Achievement Recognition:** Higher levels show your dedication
- 📊 **Progress Motivation:** Visual feedback on your learning journey
- 🎯 **Goal Setting:** Work towards reaching the next level
- 📈 **Skill Indication:** Your level reflects your learning activity

---

## Tracking Your Progress

Click **"My Progress"** in the navigation to view your learning statistics.

### Weekly Statistics

Track your performance for the current week:
- **Minutes Learned**: Total study time this week
- **Units Completed**: Lessons finished this week
- **Quiz Accuracy**: Average quiz score this week

### Lifetime Progress

View your all-time achievements:
- **Total Minutes**: Cumulative study time
- **Lessons Completed**: Total lessons finished
- **Quizzes Taken**: Number of quizzes attempted
- **Overall Accuracy**: Average quiz score across all time

### Empty State

If you haven't completed any lessons yet, you'll see a call-to-action to start learning.

---

## Security & Privacy

### Account Security

**Your account is protected by:**
- Secure password validation
- Login attempt logging
- Session management
- HTTPS encryption (production)

### Privacy

**We protect your data:**
- All account changes are logged with timestamps
- Password reset tokens expire after 20 minutes
- Generic error messages prevent account enumeration
- Your password is never stored in plain text

### Best Practices

**To keep your account secure:**
- ✅ Use a strong, unique password
- ✅ Don't share your password with anyone
- ✅ Log out when using shared computers
- ✅ Keep your email address up to date
- ✅ Report suspicious activity immediately

**Never:**
- ❌ Use the same password as other websites
- ❌ Share your login credentials
- ❌ Click suspicious links in emails claiming to be from us
- ❌ Ignore password change notifications you didn't request

---

## Troubleshooting

### Can't Log In

**Problem:** "Invalid username/email or password"

**Solutions:**
1. Verify you're using the correct username or email address
2. Check for typos in your password
3. Try the "Forgot Password?" link if you forgot your password
4. Try the "Forgot Username?" link if you forgot your username
5. Contact support if issue persists

---

### Email Not Received

**Problem:** Not receiving password reset or username reminder emails

**Solutions:**
1. **Check spam/junk folder**
2. **Wait a few minutes** - emails may be delayed
3. **Verify email address** - make sure you entered it correctly
4. **Request again** - the form allows retries
5. **Development mode:** Check the server console instead of email

---

### Password Reset Link Expired

**Problem:** "This password reset link is invalid or has expired"

**Solutions:**
1. Password reset links expire after **20 minutes**
2. Click **"Request New Reset Link"** on the error page
3. Or go back to the "Forgot Password?" page
4. Request a new link and use it promptly

---

### Username Already Taken

**Problem:** "This username is already taken"

**Solutions:**
1. Try a different username
2. Add numbers or underscores (e.g., "john_doe" or "john2024")
3. You can log in with either your username or email address

---

### Email Already in Use

**Problem:** "This email is already in use by another account"

**Solutions:**
1. You may already have an account - try logging in
2. Use "Forgot Password?" if you've forgotten your password
3. Use a different email address
4. Contact support if you believe this is an error

---

### Session Expired

**Problem:** Logged out unexpectedly

**Solutions:**
1. Sessions expire after 1 day of inactivity
2. Simply log in again
3. Check "Remember me" to extend session
4. Your progress is saved - you won't lose any data

---

## Getting Help

### In-App Support

*Coming Soon:* A searchable help/wiki section will be added to the platform for quick answers to common questions.

### Contact Support

For issues not covered in this guide:

1. **Check this guide first** - most questions are answered here
2. **Try troubleshooting steps** - many issues have simple solutions
3. **Report bugs** - Open an issue on GitHub
4. **Request features** - Submit suggestions through GitHub

### Admin Assistance

If you're having account-related issues that can't be resolved:
- Administrators can reset your password if needed
- Contact your platform administrator for assistance
- See [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for admin contact information

---

## Quick Reference

### Common Tasks

| Task | Location | Notes |
|------|----------|-------|
| Take placement test | Onboarding menu | Determines proficiency level |
| Start a lesson | Lessons → Select lesson | Flashcards or quizzes |
| View daily quests | Dashboard → Daily Quests | Refreshes daily at midnight |
| Check XP/Level | Dashboard or Progress | Track your advancement |
| Update email | Account → Update Email | Requires password |
| Update name | Account → Update Name | First name required |
| Update username | Account → Update Username | Must be unique |
| Change password | Account → Change Password | Requires current password |
| Upload avatar | Account → Update Profile Picture | Max 5MB, PNG/JPG |
| Reset password | Login → Forgot Password? | Link expires in 20 min |
| Get username | Login → Forgot Username? | Sent via email |
| View progress | Progress in navigation | Real-time statistics |
| View quest history | Daily Quests → Quest History | Past completions |
| Access dashboard | Dashboard in navigation | Personal overview |

### Navigation Structure

**When Logged Out:**
- Home
- Lessons (shows login prompt)
- Progress (shows login prompt)
- Login
- Get Started

**When Logged In:**
- Home
- Dashboard
- Lessons
- Progress
- Daily Quests (via Dashboard)
- Admin (staff only)
- Profile Picture (dropdown menu):
  - Account
  - Logout

### Password Requirements Checklist

- [ ] At least 8 characters
- [ ] Not a common password
- [ ] Not entirely numeric
- [ ] Not too similar to your email/name

### Security Reminders

- 🔒 Always log out on shared computers
- 📧 Keep your email address current
- 🔑 Use a strong, unique password
- ⏰ Password reset links expire in 20 minutes
- 📝 All account changes are logged

---

## Updates & Changes

This guide is updated regularly as new features are added to the platform.

**Last Updated:** November 13, 2025

**Recent Changes:**
- Added placement test/onboarding section
- Added learning with lessons section (flashcards & quizzes)
- Added daily quests system documentation
- Added XP and leveling system guide
- Updated dashboard features description
- Updated navigation structure
- Modernized UI and user experience

---

## Glossary

**Account:** Your user profile and login credentials
**Avatar:** Your profile picture (custom upload or Gravatar)
**Dashboard:** Your personal overview page with XP, quests, and recommendations
**Daily Quest:** Time-limited challenges that refresh every 24 hours
**Flashcard:** Interactive vocabulary card that flips to show translation
**Lesson:** A learning module with either flashcards or quiz questions
**Level:** Your current rank based on total XP earned
**Placement Test:** Initial assessment to determine your proficiency level
**Progress:** Statistics tracking your learning achievements
**Proficiency Level:** Your skill rating (Beginner, Intermediate, Advanced)
**Quest History:** Archive of all completed daily quests
**Session:** The period you're logged in
**Streak:** Consecutive days of learning activity
**Token:** A secure temporary code for password reset
**Username:** Your unique identifier that can be used to log in (along with email)
**XP (Experience Points):** Points earned for completing lessons and quests
**Staff:** Users with admin privileges

---

**Thank you for using the Language Learning Platform!**

We're committed to helping you achieve your language learning goals. Happy learning! 🌍📚

