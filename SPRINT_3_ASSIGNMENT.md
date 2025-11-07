Sprint 3 - CS 4300 and CS 5300

Sprint 3 Objectives:

1) Project in GitHub (0pts)

2) NEW: Features with tests (40pts)

3) 80% Test coverage metrics (15pts)

4) CI Pipeline

– AI Code Review using OpenAI Platform for each Pull Request (2.5pts)

– Running automated tests for each commit (2.5pts)

– Reports test coverage metrics in console for each commit (2.5pts)

            – NEW: PyLint and/or Flake 8: Linting scans in CI pipeline w/ reports (15pts)

            – NEW: Dependabot: Dependency Vulnerability Scans in CI pipeline w/ reports (15pts)

5) Deployed to a production environment 

            – NEW: With a custom domain name (no sub domains unless you own the top level domain) (5pts)

6)  CD Pipeline that runs when code is merged into master/main (2.5pts)

– Code must continually be deployed to production environment using GitHub actions

Demo Expectations:

1) Share the URL to your production deployment so we can follow along
2) Tell us about your application and why you’re making it
3) Go through Zenhub / GitHub projects and show us what work you completed based on user story
4) Demo the work you completed on the production environment showing the feature in production and showing us the CD pipeline and test cases used to test each requirement
5) Get customer feedback

Each sprint is two weeks long. Make sure that you work through both weeks of the sprint to achieve your tasks!

Common Sprint Requirements:

    At the beginning of the sprint, meet with your group to do backlog grooming and prioritization. At this point, it’d help for you to mark stories that are MVPs (minimum viable product). 

    Begin the Sprint by looking over your backlog. Add stories or divide stories as needed- some of this may include playing Planning Poker in your team to determine points and need for division.
    Record the changes in Zenhub / GitHub.
    Meet with your customer to identify the stories they want you to implement- Prioritize and confirm with them (if you can).

    The number of stories that you will complete each sprint depends a lot on the difficulty of the stories.  Select as many stories as you hope to get done in the first sprint- if you don’t meet your expectations, that’s okay, but each person should have a story/stories to work on. You will balance the workload between each of the sprints. In Sprint 1, you will begin working on these stories. At least two larger stories should be implemented and fully tested each sprint. Pairs of students may work on features that are especially large.
    Move the selected tasks from Backlog to Sprint1.
    Each group member should take ownership of AT LEAST one task.

Keep the FIRST and SMART principles in mind- it is fine to divide stories and tasks so that they are achievable and measurable.

Note: MVPs should be prioritized. We only have 4 iterations, so pick what’s really important!  It is good to have a few extra MVPs/non-MVPs assigned to the sprint that can be ready to be assigned and moved on as initial tasks are completed.

    2)   All stories selected for a sprint should be assigned to a main person and include unit / integration tests.

3) Follow the Red-Red-Green-Green-Refactor process. You  don’t need to worry about refactoring yet (end of semester)

Given your task, you are responsible for full stack development. In other words, you are responsible for building both the front end and the back end of your SaaS application and perform the associated integration and unit level testing. (In Sprint  2, metrics will be added to measure your amount/quality  of testing, so start now.)

Note that communication and the use of branches will be key here. Push, pull, and merge  to main frequently. I have put protections on the main branch,  so approval must be given for your merge to main to go through. WORK EARLY so that your branch is submitted in time for approval.

4) As you finish tasks, move them along to completion in your project management tool

Submission:

    On Canvas (1 person):

    Submit your github address
    Submit your application's devedu.io app URL of the current deployment
    Submit a short report of what was implemented and tested. You may have not completed everything.  Include that in your report  discussing what you will do.
    If your plan changed since your last submission, explain why.
    If you are having issues with some of your tests, document why.  
    At the end of the document, record your velocity (reported in Zenhub) for later use.

    On Github:

    Make sure that all project files including your tests and code are committed and pushed to Github on the main branch.
    ALL students should be pushing to github. Make sure your name is associated with your github pushes (For help here: https://help.github.com/articles/setting-your-username-in-git/) so that you are not penalized for not contributing.
    Tag your git repository revision with “sprinti” where i is the sprint number and j is the deadline number. For example, for Sprint 1, you should tag your revision with “sprint1”

    To tag the current revision: git tag -a sprint1
    Warning: You must explicitly push your tags with the command git push --tags. Before you submit, please make sure that we can checkout the tag-- you can try this from the command line and also check the github website to double check that the tag is there.
    Information on github tags: git allows you to associate tags---symbolic names---with particular commits. For example, immediately after doing a commit, you could say git tag sprinti-j , and thereafter you could use git diff sprinti-j to see differences since that commit, rather than remembering its commit ID. Note that after creating a tag in your local repo, you need to say git push origin --tags to push the tags to a remote
    On Zenhub/GitHub Projects: Show your point assignments, “employee” assignments, and progress as described above. 