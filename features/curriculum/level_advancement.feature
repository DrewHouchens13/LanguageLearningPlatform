Feature: Level Advancement Through Adaptive Tests
  As a learner
  I want to take adaptive tests and advance levels
  So that I can progress through the curriculum systematically

  Background:
    Given I am logged in as "learner@example.com"
    And the curriculum system has Spanish Level 1 content
    And I have completed all 5 lessons in Level 1

  Scenario: Take adaptive test after completing lessons
    Given I have completed all 5 lessons in Spanish Level 1
    When I click "Take Test"
    Then I should see a 10-question adaptive test
    And the test should be timed (15 minutes)
    And I should see questions from different skills

  Scenario: Pass test and advance level
    Given I am taking the Spanish Level 1 test
    When I answer 9 out of 10 questions correctly (90%)
    And I submit the test
    Then I should see a passing score of 90%
    And I should see a congratulations message
    And I should advance to Level 2
    And Level 2 should become unlocked
    And I should see "New lessons available!"

  Scenario: Fail test and retry cooldown
    Given I am taking the Spanish Level 1 test
    When I answer 7 out of 10 questions correctly (70%)
    And I submit the test
    Then I should see a failing score of 70%
    And I should see a message to review lessons
    And I should see when I can retry (24 hours)
    And I should not advance to Level 2
    And Level 2 should remain locked

  Scenario: Retry test after cooldown
    Given I failed the Spanish Level 1 test 25 hours ago
    When I visit the Level 1 module page
    Then I should see the "Take Test" button enabled
    And I should be able to retake the test

  Scenario: Test adaptive question distribution
    Given I have weak vocabulary skills (45% mastery)
    And I have strong grammar skills (80% mastery)
    When I take the adaptive test
    Then 70% of questions should be from weak skills (vocabulary)
    And 30% of questions should be from strong skills (grammar)

  Scenario: View test results
    Given I have completed the Spanish Level 1 test
    When I view the test results page
    Then I should see my score
    And I should see which questions I got correct
    And I should see which questions I got wrong
    And I should see explanations for incorrect answers
    And I should see skill breakdown (vocabulary: X%, grammar: Y%)

  Scenario: Reach maximum level
    Given I am at Spanish Level 10
    And I have completed all 5 lessons in Level 10
    When I pass the Level 10 test
    Then I should see a congratulations message
    And I should see "You've mastered Level 10!"
    And I should be encouraged to continue practicing
    And I should remain at Level 10 (no advancement)

  Scenario: Test attempt tracking
    Given I am taking the Spanish Level 1 test
    When I submit the test
    Then my test attempts should increment
    And my best score should be recorded
    And my last test date should be updated

