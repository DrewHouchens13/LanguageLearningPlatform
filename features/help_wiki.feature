Feature: Help and Wiki System
  As a user of the Language Learning Platform
  I want to access comprehensive help documentation
  So that I can learn how to use the platform effectively

  Background:
    Given the application is running
    And the database is initialized

  # ============================================
  # NAVBAR HELP BUTTON SCENARIOS
  # ============================================

  Scenario: Help button appears in navigation bar for logged-out users
    Given I am on the home page
    Then I should see a "Help" button in the navigation bar
    And the "Help" button should have a question mark icon

  Scenario: Help button appears in navigation bar for logged-in users
    Given I am a logged-in user
    When I navigate to the dashboard
    Then I should see a "Help" button in the navigation bar
    And the "Help" button should be positioned between "Progress" and "Account"

  Scenario: Help button appears for admin users
    Given I am a logged-in admin user
    When I navigate to the dashboard
    Then I should see a "Help" button in the navigation bar

  # ============================================
  # USER HELP/WIKI ACCESS SCENARIOS
  # ============================================

  Scenario: Regular user clicks Help button
    Given I am a logged-in user
    When I click the "Help" button in the navigation bar
    Then I should be redirected to "/help/"
    And I should see the page title "Help & Documentation"
    And I should see a comprehensive user guide

  Scenario: Guest user accesses help page directly
    Given I am not logged in
    When I navigate to "/help/"
    Then I should see the help page
    And I should not be prompted to log in
    And I should see general platform documentation

  # ============================================
  # ADMIN HELP ACCESS SCENARIOS
  # ============================================

  Scenario: Admin user sees both User and Admin guide options
    Given I am a logged-in admin user
    When I navigate to "/help/"
    Then I should see a "User Guide" tab
    And I should see an "Admin Guide" tab
    And the "User Guide" tab should be active by default

  Scenario: Admin user switches to Admin Guide
    Given I am a logged-in admin user
    And I am on the help page
    When I click the "Admin Guide" tab
    Then I should see admin-specific documentation
    And I should see sections for "Managing Users", "Managing Lessons", "Managing Daily Quests"
    And the "Admin Guide" tab should be highlighted as active

  Scenario: Regular user cannot see Admin Guide tab
    Given I am a logged-in user without admin privileges
    When I navigate to "/help/"
    Then I should see the "User Guide"
    But I should not see an "Admin Guide" tab

  # ============================================
  # WIKI STRUCTURE AND NAVIGATION SCENARIOS
  # ============================================

  Scenario: Help page displays table of contents
    Given I am on the help page
    Then I should see a "Table of Contents" sidebar
    And the table of contents should include:
      | Section                  |
      | Getting Started          |
      | Creating an Account      |
      | Taking Lessons           |
      | Daily Quests             |
      | XP and Leveling          |
      | Managing Your Account    |
      | Troubleshooting          |

  Scenario: User clicks on a table of contents link
    Given I am on the help page
    When I click "Daily Quests" in the table of contents
    Then the page should scroll to the "Daily Quests" section
    And the "Daily Quests" section should be highlighted

  Scenario: Help page has breadcrumb navigation
    Given I am on the help page viewing "Daily Quests" section
    Then I should see breadcrumb navigation "Home > Help > Daily Quests"
    And I can click "Home" to return to the dashboard

  # ============================================
  # HELP PAGE CONTENT SCENARIOS
  # ============================================

  Scenario: User guide displays comprehensive sections
    Given I am on the help page
    Then I should see the following sections in order:
      | Section                       |
      | Getting Started               |
      | Creating an Account           |
      | Taking the Placement Test     |
      | Learning with Lessons         |
      | Daily Quests                  |
      | XP and Leveling System        |
      | Tracking Your Progress        |
      | Managing Your Account         |
      | Password & Username Recovery  |
      | Security & Privacy            |
      | Troubleshooting               |

  Scenario: Each help section has expandable/collapsible content
    Given I am on the help page
    When I view the "Getting Started" section
    Then the section should be expanded by default
    When I click the "Creating an Account" section header
    Then the "Creating an Account" section should expand
    And I should see step-by-step instructions

  Scenario: Help page includes screenshots and examples
    Given I am on the help page
    When I view the "Taking Lessons" section
    Then I should see example screenshots of lesson pages
    And I should see example quiz questions with explanations

  # ============================================
  # SEARCH FUNCTIONALITY SCENARIOS
  # ============================================

  Scenario: Help page has a search bar
    Given I am on the help page
    Then I should see a search bar at the top
    And the search bar should have placeholder text "Search help articles..."

  Scenario: User searches for help topic
    Given I am on the help page
    When I type "daily quests" in the search bar
    And I press Enter
    Then I should see search results for "daily quests"
    And the results should highlight matching sections
    And I should see links to "Daily Quests" and "Quest History"

  Scenario: Search returns no results
    Given I am on the help page
    When I type "nonexistent topic xyz" in the search bar
    And I press Enter
    Then I should see a message "No results found for 'nonexistent topic xyz'"
    And I should see a suggestion "Try different keywords or browse the table of contents"

  Scenario: Search results are clickable
    Given I am on the help page
    And I have searched for "password reset"
    When I click on the first search result
    Then I should be taken to the "Password & Username Recovery" section
    And the relevant text should be highlighted

  # ============================================
  # ADMIN GUIDE SPECIFIC SCENARIOS
  # ============================================

  Scenario: Admin guide displays admin-specific content
    Given I am a logged-in admin user
    And I am on the help page
    When I click the "Admin Guide" tab
    Then I should see the following admin sections:
      | Admin Section                  |
      | Creating Admin Accounts        |
      | Managing Users                 |
      | Managing Lessons               |
      | Managing Daily Quests          |
      | Viewing User Progress          |
      | Bulk Operations                |
      | Security Best Practices        |
      | Troubleshooting Admin Issues   |

  Scenario: Admin guide includes bulk operation examples
    Given I am a logged-in admin user
    And I am viewing the "Admin Guide"
    When I navigate to the "Bulk Operations" section
    Then I should see step-by-step instructions for:
      | Operation                          |
      | Resetting multiple user passwords  |
      | Making users administrators        |
      | Resetting user progress            |
    And each operation should include screenshots

  # ============================================
  # MOBILE RESPONSIVENESS SCENARIOS
  # ============================================

  Scenario: Help page is mobile responsive
    Given I am on the help page
    When I view the page on a mobile device
    Then the table of contents should collapse into a hamburger menu
    And the search bar should remain accessible
    And the content should be readable without horizontal scrolling

  Scenario: Mobile user opens table of contents menu
    Given I am on the help page on a mobile device
    When I tap the hamburger menu icon
    Then the table of contents should slide in from the left
    And I can tap any section to navigate
    When I tap a section
    Then the menu should close automatically

  # ============================================
  # ACCESSIBILITY SCENARIOS
  # ============================================

  Scenario: Help page is keyboard navigable
    Given I am on the help page
    When I press the Tab key repeatedly
    Then the focus should move through all interactive elements in order:
      | Element                    |
      | Search bar                 |
      | Table of contents links    |
      | Section headers            |
      | Expandable content areas   |
      | Back to top button         |

  Scenario: Help page has proper ARIA labels
    Given I am on the help page
    Then the search bar should have aria-label "Search help documentation"
    And the table of contents should have aria-label "Help topics navigation"
    And expandable sections should have aria-expanded attributes

  # ============================================
  # QUICK ACCESS SCENARIOS
  # ============================================

  Scenario: Help page has "Back to Top" button
    Given I am on the help page
    When I scroll down to the "Troubleshooting" section
    Then I should see a "Back to Top" button in the bottom-right corner
    When I click the "Back to Top" button
    Then the page should smoothly scroll to the top

  Scenario: Related help links within content
    Given I am on the help page viewing "Daily Quests" section
    Then I should see inline links to related topics like:
      | Related Topic              |
      | XP and Leveling System     |
      | Tracking Your Progress     |
    When I click "XP and Leveling System"
    Then I should navigate to that section

  # ============================================
  # EXTERNAL DOCUMENTATION LINKS
  # ============================================

  Scenario: Help page links to external resources
    Given I am on the help page
    Then I should see a "Need More Help?" section at the bottom
    And I should see a link to "Contact Support"
    And I should see a link to "GitHub Issues" for bug reports
    And external links should open in a new tab

  # ============================================
  # HELP CONTEXT INTEGRATION SCENARIOS
  # ============================================

  Scenario: Contextual help links from feature pages
    Given I am on the "Daily Quests" page
    When I click a "Learn More" icon next to a quest
    Then I should be redirected to "/help/#daily-quests"
    And the "Daily Quests" section should be expanded and highlighted

  Scenario: Help link in error messages
    Given I receive an error message "Password reset link expired"
    Then I should see a link "Learn more about password recovery"
    When I click the link
    Then I should be taken to "/help/#password-recovery"

  # ============================================
  # AI CHATBOT ASSISTANT SCENARIOS
  # ============================================

  Scenario: Chatbot button appears on all pages
    Given I am on any page of the platform
    Then I should see a floating chatbot button in the bottom-right corner
    And the chatbot button should have a chat bubble icon
    And the button should display "Help Assistant" tooltip on hover

  Scenario: Chatbot button is visible for guest users
    Given I am not logged in
    And I am on the home page
    Then I should see the chatbot button
    And the button should be accessible

  Scenario: Chatbot button is visible for logged-in users
    Given I am a logged-in user
    And I am on the dashboard
    Then I should see the chatbot button
    And the button should remain fixed during scrolling

  Scenario: Chatbot button is visible for admin users
    Given I am a logged-in admin user
    And I am on the admin page
    Then I should see the chatbot button
    And the button should be accessible from admin interface

  Scenario: User opens chatbot window
    Given I am on the dashboard
    When I click the chatbot button
    Then a chat window should slide in from the right side
    And the chat window should have a header "Help Assistant"
    And I should see a welcome message "Hi! I'm your help assistant. Ask me anything about using the platform!"
    And I should see a text input field with placeholder "Type your question..."
    And the chatbot button should hide or change to a close icon

  Scenario: Chatbot window displays properly
    Given I have opened the chatbot window
    Then the window should be 400px wide on desktop
    And the window should be 100% width on mobile
    And the window should have a close button in the top-right
    And the window should have a message history area
    And the window should have an input area at the bottom

  Scenario: User closes chatbot window
    Given the chatbot window is open
    When I click the close button
    Then the chat window should slide out to the right
    And the chatbot button should reappear
    And my chat history should be preserved

  Scenario: User closes chatbot by clicking outside
    Given the chatbot window is open
    When I click outside the chat window on the main page
    Then the chat window should close
    And the chatbot button should reappear

  Scenario: User asks a simple question in chatbot
    Given the chatbot window is open
    When I type "How do I complete daily quests?" in the chat input
    And I press Enter
    Then I should see my message displayed in the chat history
    And I should see a typing indicator "Assistant is typing..."
    And I should receive an AI response within 5 seconds
    And the response should reference the Daily Quests documentation
    And the response should include a link to "/help/#daily-quests"

  Scenario: Chatbot searches user documentation for regular users
    Given I am a logged-in user without admin privileges
    And the chatbot window is open
    When I ask "How do I reset my password?"
    Then the AI should search the User Guide documentation
    And the response should include step-by-step password reset instructions
    And the response should include a link to the password recovery help section
    But the response should not include admin-specific information

  Scenario: Chatbot searches both user and admin documentation for admins
    Given I am a logged-in admin user
    And the chatbot window is open
    When I ask "How do I reset user passwords?"
    Then the AI should search both User Guide and Admin Guide documentation
    And the response should include admin-specific password reset instructions
    And the response should mention both user self-service and admin bulk operations
    And the response should include links to relevant admin guide sections

  Scenario: Chatbot provides context-aware responses for admins
    Given I am a logged-in admin user
    And I am on the admin users page
    And the chatbot window is open
    When I ask "How do I use bulk actions?"
    Then the AI should detect I'm on the admin page
    And the response should prioritize admin-specific bulk action documentation
    And the response should include examples from the Admin Guide

  Scenario: User asks multiple questions in sequence
    Given the chatbot window is open
    When I ask "What are daily quests?"
    And I receive a response about daily quests
    And I ask "How do I complete them?"
    Then the AI should understand the context of the previous question
    And the response should provide completion instructions for daily quests
    And both messages should remain in the chat history

  Scenario: Chatbot maintains conversation context
    Given I have had a conversation about daily quests
    When I ask a follow-up question "What rewards do I get?"
    Then the AI should understand I'm still asking about daily quests
    And the response should explain XP rewards for quest completion
    And should not require me to re-explain what I'm asking about

  Scenario: Chatbot handles unclear questions
    Given the chatbot window is open
    When I ask "How do I do the thing?"
    Then the AI should ask clarifying questions like:
      | Clarification                                      |
      | Could you please be more specific?                 |
      | Are you asking about lessons, quests, or account? |
    And should provide common topic suggestions

  Scenario: Chatbot handles questions outside documentation scope
    Given the chatbot window is open
    When I ask "What's the weather today?"
    Then the AI should politely redirect with a message like:
      """
      I'm specifically designed to help with the Language Learning Platform.
      I can answer questions about lessons, daily quests, account management, and more.
      Try asking something like "How do I earn XP?" or "What are daily quests?"
      """

  Scenario: Chatbot provides helpful links in responses
    Given the chatbot window is open
    When I ask "How do I change my email?"
    Then the response should include step-by-step instructions
    And the response should include a clickable link to "/help/#managing-your-account"
    And the response should include a clickable link to "/account/" to go directly to account settings
    When I click the help documentation link
    Then I should be taken to the help page with the relevant section highlighted
    And the chatbot window should remain open

  Scenario: Chatbot handles API errors gracefully
    Given the chatbot window is open
    And the OpenAI API is unavailable
    When I ask a question
    Then I should see an error message:
      """
      Sorry, I'm having trouble connecting right now.
      Please try again in a moment or browse the Help page directly.
      """
    And I should see a button "Go to Help Page"
    And my question should remain in the input field

  Scenario: Chatbot handles rate limiting
    Given the chatbot window is open
    And I have asked many questions quickly
    When the OpenAI API rate limit is reached
    Then I should see a friendly message:
      """
      I need a quick break! Please wait a moment before asking another question.
      In the meantime, you can browse the Help documentation.
      """
    And I should see a countdown timer "Try again in 30 seconds"

  Scenario: Chatbot shows typing indicator
    Given the chatbot window is open
    When I send a question
    Then I should immediately see a typing indicator
    And the indicator should show "Assistant is typing..."
    And the indicator should have animated dots
    When the AI response is received
    Then the typing indicator should disappear
    And the response should appear

  Scenario: User can copy chatbot responses
    Given the chatbot window is open
    And I have received a response from the assistant
    When I hover over the response message
    Then I should see a "Copy" button
    When I click the "Copy" button
    Then the response text should be copied to my clipboard
    And I should see a confirmation "Copied!"

  Scenario: Chatbot displays timestamps
    Given the chatbot window is open
    And I have had a conversation
    Then each message should display a timestamp
    And timestamps should be in format "2:30 PM"
    And messages from today should show time only
    And messages from previous days should show date and time

  Scenario: Chat history persists across page navigation
    Given I have had a conversation in the chatbot
    When I navigate to a different page
    And I open the chatbot again
    Then I should see my previous conversation history
    And the context should be maintained

  Scenario: Chat history persists in session storage
    Given I have had a conversation in the chatbot
    When I refresh the page
    And I open the chatbot
    Then my conversation history should still be visible
    And I can continue the conversation from where I left off

  Scenario: User can clear chat history
    Given the chatbot window is open
    And I have conversation history
    When I click the "Clear Chat" button in the header
    Then I should see a confirmation dialog "Are you sure you want to clear chat history?"
    When I confirm
    Then all messages should be removed
    And I should see the welcome message again

  Scenario: Chatbot responses include relevant screenshots
    Given the chatbot window is open
    When I ask "How do I take a lesson?"
    Then the AI response should include text instructions
    And the response should include a thumbnail screenshot of a lesson page
    When I click the screenshot
    Then it should expand in a lightbox view

  Scenario: Chatbot suggests related topics
    Given the chatbot window is open
    When I ask about "daily quests"
    And I receive a response
    Then I should see a "Related Topics" section with:
      | Related Topic          |
      | XP and Leveling        |
      | Quest History          |
      | Tracking Your Progress |
    When I click a related topic
    Then the chatbot should automatically explain that topic

  Scenario: Chatbot is mobile responsive
    Given I am on a mobile device
    When I open the chatbot
    Then the chat window should take up full screen width
    And the window should slide in from the bottom
    And the close button should be easily tappable
    And the input field should not be covered by the keyboard

  Scenario: Mobile user can minimize chatbot
    Given I am on a mobile device
    And the chatbot is open
    When I swipe down on the chat header
    Then the chat should minimize to a small badge
    And the badge should show unread message count if assistant responds
    When I tap the minimized badge
    Then the chat should expand again

  Scenario: Chatbot respects user privacy
    Given I am using the chatbot
    Then I should see a privacy notice at the bottom:
      """
      Your questions help improve our documentation.
      We don't store personally identifiable information.
      """
    And I should see a link to the Privacy Policy

  Scenario: Admin asks admin-specific questions
    Given I am a logged-in admin user
    And the chatbot window is open
    When I ask "How do I create bulk user accounts?"
    Then the response should reference the Admin Guide
    And should include instructions for bulk operations
    And should include a link to "/help/#admin-guide"
    And should mention the admin panel location

  Scenario: Chatbot handles multilingual questions
    Given the chatbot window is open
    When I ask "¿Cómo completo una lección?" (Spanish for "How do I complete a lesson?")
    Then the AI should detect the language
    And should respond in Spanish with lesson completion instructions
    And should provide a translation toggle button
    When I click "Translate to English"
    Then the response should be translated to English

  Scenario: Chatbot provides quick action buttons
    Given the chatbot window is open
    When I ask "How do I reset my password?"
    Then the response should include text instructions
    And should include a quick action button "Reset Password Now"
    When I click the quick action button
    Then I should be taken to "/password-reset/"
    And the chatbot should remain open

  Scenario: Chatbot offers feedback mechanism
    Given the chatbot window is open
    And I have received a response
    Then I should see feedback buttons below the response:
      | Feedback Option |
      | 👍 Helpful      |
      | 👎 Not helpful  |
    When I click "👍 Helpful"
    Then I should see a confirmation "Thanks for your feedback!"
    And the feedback should be logged anonymously

  Scenario: Chatbot provides negative feedback options
    Given the chatbot window is open
    And I have received a response
    When I click "👎 Not helpful"
    Then I should see options:
      | Reason                        |
      | Answer was unclear            |
      | Didn't answer my question     |
      | Information seems incorrect   |
    When I select a reason
    Then I should see "Thank you. We'll work on improving our help system."

  Scenario: Chatbot suggests contacting support for unresolved issues
    Given the chatbot window is open
    And I have marked multiple responses as "Not helpful"
    Then the chatbot should offer:
      """
      I apologize I couldn't help resolve your issue.
      Would you like to contact our support team directly?
      """
    And I should see a button "Contact Support"
    When I click "Contact Support"
    Then I should be taken to a contact form with my chat history pre-filled

  Scenario: Keyboard shortcuts for chatbot
    Given I am on any page
    When I press "Ctrl+/" or "Cmd+/" (help shortcut)
    Then the chatbot window should open
    And the input field should be focused
    When I press "Escape"
    Then the chatbot window should close

  Scenario: Chatbot input supports markdown preview
    Given the chatbot window is open
    When I type a long, detailed question with formatting
    Then I should see a character count "250/500 characters"
    And if I exceed 500 characters I should see a warning
    And I should see a "Send" button become enabled when I type

  Scenario: Chatbot handles network disconnection
    Given the chatbot window is open
    And my internet connection drops
    When I send a message
    Then I should see an error:
      """
      No internet connection detected.
      Your message will be sent when you're back online.
      """
    And the message should be queued
    When my connection is restored
    Then the queued message should be sent automatically
