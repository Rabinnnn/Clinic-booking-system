# AI USAGE

**1. What did you use AI for across the four sections?**
- I used AI to help with the system design in terms of determining the core domain entities, fields, component layers, and some business logic.
- Writing the appropriate code based on the final system design (after I made some few changes). 
- Writing tests to uphold the validity and integrity of the code.
- Writing the CI/CD workflow script

**2. Give one example where an AI suggestion improved your work. What did you prompt it with?**
- I was trying to restrict the available booking slots to fall within the working hours of 8am to 5pm but in some instances the restriction was failing. The prompt: "How do i ensure that the available booking slots displayed fall within 8am-5pm regardless of time format?" It then suggested that I use UTC methods instead of converting datetimes to local timezone which tends to cause shifts.

**3. Give one example where AI output was wrong or
incomplete and how you caught it.**
- It ended up including directory '/static/' inside the .gitignore file. The project ended up displaying wrongly after deployment since essential css and js files were not being pushed to github hence were missing in production environment.
I caught this while debugging based on the question, "why is the site displaying correctly on local env and wrongly on production yet the code is the same?". Since the issue was mainly styling, I decided to check if the css and js were present in the production environment and found out they were missing. Then I inpected the .gitignore and found the erroneous line.

**4. Name two decisions you made without
AI. Why did you trust your own judgment there?**
- For the deployment, I decided to use Render since it has a free tier and also connecting it to a github repo is straightforward. I've done the process before and so I could rely on my judgement for this.
- For the CI/CD pipeline I used GitHub Actions since I've used it before and it served me well.