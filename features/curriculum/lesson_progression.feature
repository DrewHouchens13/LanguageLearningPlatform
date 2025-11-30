Feature: Curriculum Lesson Progression
  As a learner
  I want to progress through curriculum lessons
  So that I can systematically learn a language at my level

  Background:
    Given I am logged in as "learner@example.com"
    And the curriculum system has Spanish Level 1 content

  Scenario: View curriculum overview
    Given I am learning Spanish
    When I visit the curriculum overview page
    Then I should see all 10 levels for Spanish
    And level 1 should be marked as available
    And levels 2-10 should be marked as locked

  Scenario: View module detail
    Given I am learning Spanish
    And I have access to Level 1
    When I visit the Level 1 module page
    Then I should see 5 lessons (vocabulary, grammar, conversation, reading, listening)
    And I should see a "Take Test" button that is disabled
    And the test button should show "Complete all 5 lessons first"

  Scenario: Complete a vocabulary lesson
    Given I am learning Spanish
    And I am viewing the Level 1 vocabulary lesson
    When I complete all flashcards
    And I complete the quiz with 80% score
    Then the lesson should be marked as complete
    And I should earn XP points
    And my progress should show 1/5 lessons completed

  Scenario: Complete all lessons in a module
    Given I am learning Spanish
    And I have completed 4 lessons in Level 1
    When I complete the 5th lesson
    Then my progress should show 5/5 lessons completed
    And the "Take Test" button should become enabled
    And I should see "Ready to take the test!"

  Scenario: Lesson completion tracking
    Given I am learning Spanish
    When I complete the vocabulary lesson
    And I complete the grammar lesson
    Then my module progress should show 2 completed lessons
    And I should be able to see which lessons are complete
    And I should be able to see which lessons are remaining

  Scenario: Access locked levels
    Given I am learning Spanish
    And I have not completed Level 1
    When I try to access Level 2
    Then I should be redirected to Level 1
    And I should see a message that Level 2 is locked

  Scenario: View lesson content
    Given I am learning Spanish
    And I am viewing a vocabulary lesson
    When the lesson loads
    Then I should see flashcards with Spanish words
    And I should see English translations
    And I should see a quiz section
    And I should see audio playback controls for listening practice

