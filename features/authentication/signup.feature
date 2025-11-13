Feature: User Signup
  As a new visitor
  I want to create an account
  So that I can start learning languages

  Scenario: Successful signup
    Given I am on the signup page
    When I enter full name "John Doe"
    And I enter email "john.doe@example.com"
    And I enter password "SecurePass123!"
    And I confirm password "SecurePass123!"
    And I click the signup button
    Then I should be logged in automatically
    And I should be redirected to the landing page
    And a user profile should be created for me

  Scenario: Signup with duplicate email
    Given a user exists with email "existing@example.com"
    And I am on the signup page
    When I enter full name "Jane Doe"
    And I enter email "existing@example.com"
    And I enter password "SecurePass123!"
    And I confirm password "SecurePass123!"
    And I click the signup button
    Then I should see an error message "User with this email already exists"
    And I should remain on the signup page

  Scenario: Signup with mismatched passwords
    Given I am on the signup page
    When I enter full name "John Doe"
    And I enter email "john@example.com"
    And I enter password "SecurePass123!"
    And I confirm password "DifferentPass456!"
    And I click the signup button
    Then I should see an error message "Passwords do not match"
    And I should remain on the signup page

  Scenario: Signup with weak password
    Given I am on the signup page
    When I enter full name "John Doe"
    And I enter email "john@example.com"
    And I enter password "weak"
    And I confirm password "weak"
    And I click the signup button
    Then I should see an error message about password requirements
    And I should remain on the signup page
