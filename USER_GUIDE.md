# Language Learning Platform - User Guide

Welcome to the Language Learning Platform! This guide will help you get started and make the most of your language learning journey.

## Table of Contents

- [Getting Started](#getting-started)
- [Creating an Account](#creating-an-account)
- [Logging In](#logging-in)
- [Managing Your Account](#managing-your-account)
- [Password & Username Recovery](#password--username-recovery)
- [Using the Dashboard](#using-the-dashboard)
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

---

## Logging In

1. **Go to the login page**
2. **Enter your email address** (not your username)
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
- You'll still log in with your email address (not username)
- Your username is for display purposes

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

## Password & Username Recovery

### Forgot Your Password?

1. **Go to the login page**
2. **Click "Forgot Password?"** link
3. **Enter your email address**
4. **Click "Send Reset Link"**
5. **Check your email** for the password reset link
   - In development: Check the server console
   - In production: Check your email inbox/spam folder
6. **Click the link in the email**
7. **Enter your new password** (twice)
8. **Click "Reset Password"**
9. You'll be automatically logged in

**Important:**
- Password reset links expire after **20 minutes** for security
- If your link expires, request a new one
- For security, you'll see a success message even if the email doesn't exist

### Forgot Your Username?

1. **Go to the login page**
2. **Click "Forgot Username?"** link
3. **Enter your email address**
4. **Click "Send Username"**
5. **Check your email** for your username
   - In development: Check the server console
   - In production: Check your email inbox/spam folder

**Note:** You can log in with either your username or email address.

---

## Using the Dashboard

After logging in, access your dashboard by clicking **"Dashboard"** in the navigation.

### Dashboard Features

Your dashboard shows:
- Welcome message with your name
- Your email and username
- Member since date
- Quick links to courses, progress, and study schedule

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

**Problem:** "Invalid email or password"

**Solutions:**
1. Verify you're using the correct email address
2. Check for typos in your password
3. Try the "Forgot Password?" link
4. Contact support if issue persists

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
3. Your username is just for display - you log in with email

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
| Update email | Account → Update Email | Requires password |
| Update name | Account → Update Name | First name required |
| Update username | Account → Update Username | Must be unique |
| Change password | Account → Change Password | Requires current password |
| Reset password | Login → Forgot Password? | Link expires in 20 min |
| Get username | Login → Forgot Username? | Sent via email |
| View progress | My Progress in navigation | Real-time statistics |
| Access dashboard | Dashboard in navigation | Personal overview |

### Navigation Structure

**When Logged Out:**
- Home
- Courses
- Lessons
- My Progress
- Login
- Sign Up

**When Logged In:**
- Home
- Courses
- Lessons
- My Progress
- Dashboard
- Admin (staff only)
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

**Last Updated:** October 26, 2025

**Recent Changes:**
- Added account management section
- Added password recovery guide
- Added username recovery guide
- Added security best practices
- Added troubleshooting section

---

## Glossary

**Account:** Your user profile and login credentials
**Dashboard:** Your personal overview page
**Progress:** Statistics tracking your learning achievements
**Session:** The period you're logged in
**Token:** A secure temporary code for password reset
**Username:** Your display name (different from login email)
**Staff:** Users with admin privileges

---

**Thank you for using the Language Learning Platform!**

We're committed to helping you achieve your language learning goals. Happy learning! 🌍📚

