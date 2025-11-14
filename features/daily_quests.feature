Feature: Daily Challenge System
  As a returning learner
  So that I have a reason to come back each day
  I want a daily challenge with 5 random questions that grant bonus XP

  Background:
    Given the following lessons exist with quiz questions:
      | title          | slug    | lesson_type | xp_value | questions |
      | Colors         | colors  | quiz        | 100      | 10        |
      | Shapes         | shapes  | quiz        | 100      | 10        |
      | Numbers        | numbers | quiz        | 150      | 10        |
    And I am a registered user

  # NEW SYSTEM: ONE Quest Per Day with 5 Random Questions
  Scenario: Daily challenge is generated with 5 random questions
    Given today is "2025-11-13"
    And no daily quest exists for today
    When the system generates today's daily quest
    Then a daily quest should exist for "2025-11-13"
    And the quest should have exactly 5 questions
    And the quest title should be "Daily Challenge"
    And the quest XP reward should be 50

  Scenario: User views today's daily challenge
    Given a daily quest exists for today
    When I visit the daily quest page
    Then I should see the heading "Daily Challenge"
    And I should see "Answer 5 questions to earn bonus XP!"
    And I should see "50 XP" reward
    And I should see 5 multiple choice questions

  Scenario: User completes daily challenge successfully
    Given a daily quest exists for today
    And the quest has 5 questions
    When I view the daily quest page
    And I answer all 5 questions correctly
    And I submit the challenge
    Then I should see "Challenge Completed!"
    And I should see my score "5/5"
    And I should receive 50 XP
    And my total XP should increase by 50
    And the quest should be marked as completed

  Scenario: User completes daily challenge partially (proportional XP)
    Given a daily quest exists for today
    And the quest has 5 questions
    When I view the daily quest page
    And I answer 3 questions correctly
    And I answer 2 questions incorrectly
    And I submit the challenge
    Then I should see "Challenge Completed!"
    And I should see my score "3/5"
    And I should receive 30 XP
    And my total XP should increase by 30
    And the quest should be marked as completed

  Scenario: User can only complete daily quest once per day
    Given a daily quest exists for today
    And I have already completed today's quest
    When I visit the daily quest page
    Then I should see "Quest Completed"
    And I should see my previous score
    And I should not see a "Start Quest" button
    And I should see "Come back tomorrow for a new quest!"

  Scenario: New daily quest appears the next day
    Given I completed yesterday's quest on "2025-11-12"
    And today is "2025-11-13"
    When the system generates today's daily quest
    And I visit the daily quest page
    Then I should see a new daily quest for "2025-11-13"
    And I should see a "Start Quest" button
    And the quest should be different from yesterday's quest

  Scenario: Daily quest questions are harder than lesson questions
    Given a daily quest exists based on "Colors" lesson
    And the "Colors" lesson teaches individual colors
    When I view the daily quest questions
    Then the questions should combine multiple concepts
    And the questions should be more challenging than the lesson

  Scenario: Daily quest inherits lesson format
    Given a daily quest exists based on "Colors" flashcard lesson
    When I start the daily quest
    Then the quest should use flashcard format
    And I should see flashcard-style interactions

  Scenario: Daily quest inherits quiz format
    Given a daily quest exists based on "Numbers" quiz lesson
    When I start the daily quest
    Then the quest should use quiz format
    And I should see multiple choice questions

  Scenario: Quest pool expands with new lessons
    Given there are 3 lessons in the system
    When a new lesson "Greetings" is added
    And the system generates tomorrow's daily quest
    Then the quest could be based on any of the 4 lessons
    And the quest generation should include the new lesson

  Scenario: XP calculation is 75% of source lesson
    Given a lesson "Advanced Grammar" has 200 XP value
    When a daily quest is generated based on "Advanced Grammar"
    Then the quest XP reward should be 150
    And the reward should be 75% of the lesson XP

  Scenario: Guest users cannot access daily quests
    Given I am not logged in
    When I try to access the daily quest page
    Then I should be redirected to the login page
    And I should see "Please log in to access daily quests"

  Scenario: User sees progress during quest
    Given a daily quest exists for today with 5 questions
    When I start the daily quest
    And I answer question 1
    Then I should see "Question 1/5 completed"
    When I answer question 2
    Then I should see "Question 2/5 completed"
    When I answer question 3
    Then I should see "Question 3/5 completed"

  Scenario: User can view quest history
    Given I have completed daily quests on:
      | date       | score | xp_earned |
      | 2025-11-10 | 5/5   | 75        |
      | 2025-11-11 | 4/5   | 60        |
      | 2025-11-12 | 3/5   | 45        |
    When I visit my quest history page
    Then I should see all 3 completed quests
    And I should see the total XP earned from quests: 180

  Scenario: Quest awards XP proportional to correct answers
    Given a daily quest has 5 questions worth 75 total XP
    When I answer 4 out of 5 questions correctly
    Then I should receive 60 XP
    And the XP should be calculated as: 75 * (4/5) = 60

  Scenario: System prevents duplicate quests on same day
    Given a daily quest already exists for "2025-11-13"
    When the system attempts to generate another quest for "2025-11-13"
    Then no new quest should be created
    And the existing quest should remain unchanged

  # NEW FEATURES: Personalized Question Selection
  Scenario: Questions from completed lessons only (personalized)
    Given I have completed the "Colors" lesson
    And I have completed the "Shapes" lesson
    And I have NOT completed the "Numbers" lesson
    When the system generates today's daily quest for me
    Then the quest should have 5 questions
    And all questions should be from "Colors" or "Shapes" lessons
    And no questions should be from "Numbers" lesson

  Scenario: Questions from all lessons when none completed
    Given I have NOT completed any lessons
    When the system generates today's daily quest for me
    Then the quest should have 5 questions
    And questions may be from any available lesson

  # NEW FEATURES: Progress Page Statistics
  Scenario: View weekly challenge statistics on progress page
    Given I completed 3 daily challenges this week
    And I earned 150 XP from challenges this week
    And I answered 12 out of 15 questions correctly
    When I visit my progress page
    Then I should see "3" challenges completed this week
    And I should see "150 XP" earned from challenges
    And I should see "80%" challenge accuracy this week

  Scenario: View lifetime challenge statistics on progress page
    Given I have completed 10 daily challenges total
    And I have earned 450 XP from all challenges
    And I have 85% accuracy across all challenges
    When I visit my progress page
    Then I should see "10" total challenges completed
    And I should see "450 XP" total challenge XP earned
    And I should see "85%" lifetime challenge accuracy
    And I should see a link to "View Challenge History"

  # NEW FEATURES: Challenge History with Timezone Display
  Scenario: Challenge history displays completion times in user's local timezone
    Given I completed a challenge at "2025-11-14 14:40:00 UTC"
    And my system timezone is "MST" (UTC-7)
    When I visit my challenge history page
    Then I should see the completion time as "Nov 14, 7:40 AM"
    And the time should match my local timezone

  Scenario: Challenge history shows correct terminology
    Given I have completed 2 daily challenges
    When I visit the quest history page
    Then I should see the page title "Challenge History"
    And I should see "2 challenges completed"
    And I should see "Total Challenge XP Earned"
    And I should NOT see any references to "Quest"

  # NEW FEATURES: SOFA Service Layer (Unit Test Coverage)
  Scenario: DailyQuestService calculates weekly stats correctly
    Given I completed 3 challenges in the last 7 days
    And I answered 12 out of 15 questions correctly
    When the system calculates my weekly challenge stats
    Then the service should return 3 challenges completed
    And the service should return 80% accuracy
    And the stats should be calculated in the service layer

  Scenario: DailyQuestService calculates quest score correctly
    Given a daily challenge with 5 questions
    And I submit answers with 4 correct and 1 incorrect
    When the service calculates my score
    Then the service should return 4 correct answers
    And the service should return 5 total questions
    And the service should calculate 40 XP earned (50 * 4/5)

  # NEW FEATURES: Admin Panel Integration
  Scenario: Admin can manage daily challenges
    Given I am an admin user
    When I access the Django admin panel
    Then I should see "Daily Quests" in the admin menu
    And I should be able to create new daily quests
    And I should be able to edit quest questions inline
    And I should be able to view user quest attempts
    And I should be able to recalculate XP for attempts
