Feature: Earning XP Points
  As a logged-in user
  I want to earn XP by completing lessons
  So that I can level up and track my progress

  Background:
    Given I am logged in as "learner@example.com"
    And my current level is 1
    And I have 0 XP

  Scenario: Earn XP from completing a lesson
    Given a lesson "Spanish Colors" exists with 10 XP reward
    When I complete the lesson "Spanish Colors" with 100% accuracy
    Then I should earn 10 XP
    And my total XP should be 10
    And I should see an XP notification "+10 XP"

  Scenario: Earn bonus XP for perfect score
    Given a lesson "Spanish Shapes" exists with 10 XP reward
    When I complete the lesson "Spanish Shapes" with 100% accuracy
    Then I should earn 10 base XP
    And I should earn a 2 XP bonus for perfect score
    And my total XP should be 12

  Scenario: Earn reduced XP for low accuracy
    Given a lesson "Spanish Numbers" exists with 10 XP reward
    When I complete the lesson "Spanish Numbers" with 60% accuracy
    Then I should earn 6 XP
    And my total XP should be 6

  Scenario: Level up after earning enough XP
    Given I have 90 XP
    And level 2 requires 100 XP
    And a lesson "Spanish Colors" exists with 15 XP reward
    When I complete the lesson "Spanish Colors"
    Then I should earn 15 XP
    And my total XP should be 105
    And I should level up to level 2
    And I should see a level up notification "Level Up! You are now Level 2"

  Scenario: Track XP history
    Given I have completed 3 lessons this week
    When I view my XP history
    Then I should see all 3 XP transactions
    And each transaction should show the date, lesson name, and XP earned
