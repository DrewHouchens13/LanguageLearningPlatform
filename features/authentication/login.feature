Feature: User Login
  As a registered user
  I want to log in to my account
  So that I can access my learning progress and lessons

  Background:
    Given a user exists with email "test@example.com" and password "SecurePass123!"

  Scenario: Successful login with email
    Given I am on the login page
    When I enter email "test@example.com"
    And I enter password "SecurePass123!"
    And I click the login button
    Then I should be redirected to the landing page
    And I should see a welcome message

  Scenario: Successful login with username
    Given I am on the login page
    When I enter username "testuser"
    And I enter password "SecurePass123!"
    And I click the login button
    Then I should be redirected to the landing page
    And I should see a welcome message

  Scenario: Failed login with invalid password
    Given I am on the login page
    When I enter email "test@example.com"
    And I enter password "WrongPassword123!"
    And I click the login button
    Then I should see an error message "Invalid username/email or password"
    And I should remain on the login page

  Scenario: Failed login with nonexistent email
    Given I am on the login page
    When I enter email "nonexistent@example.com"
    And I enter password "SecurePass123!"
    And I click the login button
    Then I should see an error message "Invalid username/email or password"
    And I should remain on the login page

  Scenario: Login redirect to next page
    Given I am on the login page with next parameter "/progress/"
    When I enter email "test@example.com"
    And I enter password "SecurePass123!"
    And I click the login button
    Then I should be redirected to "/progress/"

  Scenario: Rate limiting after multiple failed attempts
    Given I am on the login page
    When I attempt to login with wrong password 5 times
    Then I should see a rate limit error message
    And I should be temporarily blocked from logging in
