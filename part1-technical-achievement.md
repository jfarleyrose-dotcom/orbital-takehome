# Most Significant Technical Achievement

## The Problem

At Unmind (a workplace mental health platform), access to product features like therapy, coaching, and learning courses was controlled by an admin uploading a CSV. For smaller clients, this worked fine. As we started signing enterprise clients with 100,000+ employees, it broke down fast.

The core issue was twofold. First, feature access had to be tightly coupled to employment status: if someone left the company, they should immediately lose access. Waiting for an admin to notice and run an export was a liability. Second, we were leaving significant growth on the table. We had the data to send highly personalised communications (a new joiner's therapy allocation, a manager's leadership training, a new parent's relevant courses) but no reliable, real-time way to act on lifecycle changes. Admins were a bottleneck, CSV data was stale, and we had no way to react to events like role changes, department moves, or becoming a manager.

## The Solution We Built

I architected and co-built an event-based employee lifecycle system. When anything significant happened to an employee (joining, leaving, changing department, changing location, becoming a manager), that event was published to an SQS queue. Our main application consumed those events and used them to do two things: update Braze user profiles and alias mappings in real time, and evaluate access rules against the new state (department, location, role) to grant or revoke feature access accordingly.

Making the Braze integration non-blocking was an early and important decision. Braze's API had latency we couldn't control, and we didn't want lifecycle processing to stall waiting on a third-party response. By handling Braze updates asynchronously via the event stream, we kept the system responsive even under load from large client onboardings.

The system also needed to handle client-supplied data gracefully. Enterprise clients sent employee data in varying formats and quality. We built a flexible ingestion layer that could accommodate different CSV structures while enforcing the data requirements we actually needed. The tricky part was balancing strictness (bad data upstream caused real access control failures downstream) with flexibility (demanding perfect data from enterprise clients immediately would have blocked sales).

## The Hard Parts

The most persistent challenge was **human data and edge cases at scale**. Our data model required unique users, but rehires (people who left and rejoined) meant the same person could legitimately appear more than once. We had to design the system to reflect this reality without becoming brittle. We built a reconciliation layer that could detect likely rehires based on matching identifiers and handle them cleanly, rather than erroring out or creating duplicate access records.

The other hard problem was **graceful degradation when client data was wrong**. Missing departments, unknown locations, mismatched identifiers: these were common on large onboardings, and each one could cascade into access rule failures affecting hundreds of users. We built validation and error surfacing into the pipeline so these issues were caught early and clearly, rather than silently producing wrong access states.

## Impact

The direct business impact was a **30% uplift in user signups** driven by the ability to send targeted, lifecycle-aware communications: telling a new joiner about their therapy allocation, a promoted manager about available training, a new parent about parental support courses. This was only possible because we now had accurate, real-time user state to act on.

Beyond signups, enterprise clients could finally trust that access control reflected their current workforce. Employees who left lost access immediately. New joiners were provisioned automatically. This removed a category of support requests and, more importantly, removed a blocker to signing larger clients.

## What I'd Do Differently

The biggest gap was the admin experience when things went wrong. During onboarding, data issues (duplicate users, missing departments, unknown locations) were escalated to engineers who would diagnose the problem and explain it back to the client's admin team. This was slow, didn't scale, and put unnecessary burden on the engineering team.

If I did this again, I'd invest earlier in **surfacing data quality issues directly and clearly to admins**, with anonymised summaries of what's wrong and why. Something like: "14 employees are missing a department and won't receive feature access until this is resolved. Download the affected rows here." This would have shortened onboarding cycles, reduced engineer involvement in support, and made clients feel more in control.

More broadly, I've come to think the measure of a good internal system isn't just whether it works: it's whether the people who operate it can understand and fix it without needing a developer in the loop. That principle now shapes how I approach building anything with an operational surface.
