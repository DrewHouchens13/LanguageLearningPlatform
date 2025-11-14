Feature: Lesson Completion
  As a learner
  I want to complete lessons and quizzes
  So that I can learn new vocabulary and track my progress

  Background:
    Given I am logged in as "learner@example.com"

  Scenario: Complete a flashcard lesson
    Given a lesson "Spanish Colors" with 10 flashcards exists
    When I view the lesson
    Then I should see all 10 flashcards
    And each flashcard should show the Spanish word and English translation

  Scenario: Take a lesson quiz
    Given I have viewed the lesson "Spanish Colors"
    And the lesson has 8 quiz questions
    When I navigate to the quiz
    Then I should see the first question
    And I should be able to select an answer
    And I should be able to submit my answer

  Scenario: Pass a quiz with high score
    Given I am taking the "Spanish Colors" quiz
    When I answer 7 out of 8 questions correctly
    And I submit the quiz
    Then I should see my score as 87.5%
    And I should see a "Great job!" message
    And the lesson should be marked as complete
    And I should earn XP points

  Scenario: Fail a quiz with low score
    Given I am taking the "Spanish Colors" quiz
    When I answer 3 out of 8 questions correctly
    And I submit the quiz
    Then I should see my score as 37.5%
    And I should see a "Keep practicing!" message
    And the lesson should not be marked as complete
    And I should earn reduced XP points

  Scenario: View quiz results
    Given I have completed the "Spanish Colors" quiz
    When I view the results page
    Then I should see which questions I got correct
    And I should see which questions I got wrong
    And I should see the correct answers for missed questions
    And I should see a link to the next lesson

  Scenario: Lesson progression
    Given I have completed "Spanish Shapes"
    And "Spanish Colors" is the next lesson
    When I finish "Spanish Shapes" quiz
    Then I should see a "Next Lesson" button
    And clicking it should take me to "Spanish Colors"

  Scenario: Track lesson attempts
    Given I have taken the "Spanish Colors" quiz 3 times
    When I view my progress page
    Then I should see 3 attempts for "Spanish Colors"
    And I should see my best score
    And I should see my most recent score
