Feature: Daily Quests
  As a returning learner
  So that I have a reason to come back each day
  I want a daily quest with challenging questions that grant bonus XP

  Background:
    Given the following lessons exist:
      | title          | slug    | lesson_type | xp_value |
      | Colors         | colors  | flashcard   | 100      |
      | Shapes         | shapes  | flashcard   | 100      |
      | Numbers        | numbers | quiz        | 150      |
    And I am a registered user

  Scenario: Daily quest is generated automatically
    Given today is "2025-11-13"
    And no daily quest exists for today
    When the system generates today's daily quest
    Then a daily quest should exist for "2025-11-13"
    And the quest should have 5 questions
    And the quest should be based on an existing lesson
    And the quest XP reward should be 25% less than the source lesson

  Scenario: User views today's daily quest
    Given a daily quest exists for today based on "Colors"
    When I visit the daily quest page
    Then I should see the quest title "Daily Colors Challenge"
    And I should see "5 questions"
    And I should see the XP reward "75 XP"
    And I should see a "Start Quest" button

  Scenario: User completes daily quest successfully
    Given a daily quest exists for today based on "Colors"
    And the quest has 5 flashcard questions
    When I start the daily quest
    And I answer all 5 questions correctly
    And I submit the quest
    Then I should see "Quest Completed!"
    And I should see "5/5 correct"
    And I should receive 75 XP
    And my total XP should increase by 75
    And the quest should be marked as completed

  Scenario: User completes daily quest partially
    Given a daily quest exists for today based on "Shapes"
    And the quest has 5 flashcard questions
    When I start the daily quest
    And I answer 3 questions correctly
    And I answer 2 questions incorrectly
    And I submit the quest
    Then I should see "Quest Completed!"
    And I should see "3/5 correct"
    And I should receive 45 XP
    And my total XP should increase by 45
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
