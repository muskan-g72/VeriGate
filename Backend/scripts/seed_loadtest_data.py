import uuid
import random
from datetime import datetime, timezone, timedelta

from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.test_suite import TestSuite
from app.models.test_case import TestCase
from app.models.verification_run import VerificationRun
from app.models.verification_result import VerificationResult

def seed():
    with SessionLocal() as db:
        print("Checking user...")
        user = db.query(User).filter(User.email == "loadtest.user@example.com").first()
        if not user:
            user = User(
                email="loadtest.user@example.com",
                password_hash=hash_password("StrongPassword123!"),
                full_name="Load Test User",
                system_role="user",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created user: {user.email} (id: {user.id})")
        else:
            print(f"Found existing user: {user.email} (id: {user.id})")

        # Check existing projects for this user
        existing_projects = db.query(Project).filter(Project.owner_id == user.id).all()
        if len(existing_projects) >= 5:
            print(f"User already has {len(existing_projects)} projects seeded.")
            first_project_id = str(existing_projects[0].id)
            print(f"Primary project ID: {first_project_id}")
            return first_project_id

        project_names = [
            ("Checkout & Payments Microservice", "Core checkout, Stripe integration, order routing"),
            ("Auth & Identity Gateway", "SSO, OAuth2, session token lifecycle, MFA services"),
            ("Inventory & Catalog Engine", "Product metadata, real-time inventory synchronizer"),
            ("Customer Notification Pipeline", "Transactional email, SMS delivery, webhook dispatcher"),
            ("Analytics & Audit Stream", "Event capture, user telemetry, GDPR audit logging"),
        ]

        created_projects = []
        created_suites = []
        created_cases = []
        created_runs = []

        now = datetime.now(timezone.utc)

        for p_idx, (p_name, p_desc) in enumerate(project_names, 1):
            project = Project(
                name=p_name,
                description=p_desc,
                owner_id=user.id,
                github_repo=f"verigate-org/service-{p_idx}",
                github_default_branch="main",
                github_verification_enabled=False,
            )
            db.add(project)
            db.flush()
            created_projects.append(project)

            member = ProjectMember(
                project_id=project.id,
                user_id=user.id,
                role="owner",
            )
            db.add(member)

            # 4 test suites per project (total 20 suites)
            suite_types = ["Smoke Tests", "Regression Suite", "Integration Contract", "Edge Case Scenarios"]
            for s_idx, s_type in enumerate(suite_types, 1):
                suite = TestSuite(
                    project_id=project.id,
                    name=f"{p_name[:20]} - {s_type}",
                    description=f"Automated verification suite for {s_type.lower()}",
                )
                db.add(suite)
                db.flush()
                created_suites.append(suite)

                # 10 test cases per suite (total 200 cases)
                for tc_idx in range(1, 11):
                    tc = TestCase(
                        test_suite_id=suite.id,
                        title=f"Verify {s_type} Case #{tc_idx}: Endpoint response validation",
                        description=f"Validate contract integrity and status code for scenario {tc_idx}",
                        steps="1. Dispatch mock payload\n2. Verify HTTP 200 OK\n3. Assert JSON response schema",
                        expected_result="200 OK with compliant payload",
                        execution_mode="automated" if tc_idx % 2 == 0 else "manual",
                        priority="high" if tc_idx <= 3 else "medium",
                        is_active=True,
                    )
                    db.add(tc)
                    db.flush()
                    created_cases.append(tc)

        db.commit()

        # Seed 50 verification runs distributed across the 20 test suites
        statuses = ["passed", "passed", "passed", "failed", "completed"]
        for r_idx in range(1, 51):
            selected_suite = created_suites[r_idx % len(created_suites)]
            run_status = statuses[r_idx % len(statuses)]
            started_offset = timedelta(days=random.randint(1, 30), minutes=random.randint(1, 60))
            run_started = now - started_offset
            run_completed = run_started + timedelta(seconds=random.randint(45, 300))

            vrun = VerificationRun(
                test_suite_id=selected_suite.id,
                created_by_id=user.id,
                name=f"Run #{r_idx}: Automated Build Verification v{r_idx}.0",
                status=run_status,
                trigger_source="manual" if r_idx % 3 == 0 else "github_pr",
                started_at=run_started,
                completed_at=run_completed,
                pr_number=100 + r_idx if r_idx % 2 == 0 else None,
                pr_title=f"PR #{100 + r_idx}: Performance and contract upgrade" if r_idx % 2 == 0 else None,
            )
            db.add(vrun)
            db.flush()
            created_runs.append(vrun)

            # Get test cases for this suite
            suite_tcs = [tc for tc in created_cases if tc.test_suite_id == selected_suite.id]
            for tc in suite_tcs:
                res_status = "passed" if run_status in ("passed", "completed") else random.choice(["passed", "failed"])
                res = VerificationResult(
                    verification_run_id=vrun.id,
                    test_case_id=tc.id,
                    status=res_status,
                    actual_result="Execution matches expected assertion" if res_status == "passed" else "Assertion failed: response code 500",
                    notes="Automated executor verification pass" if res_status == "passed" else "Unexpected nil pointer exception",
                )
                db.add(res)

        db.commit()

        print(f"Successfully seeded:")
        print(f"  - User: {user.email}")
        print(f"  - Projects: {len(created_projects)}")
        print(f"  - Test Suites: {len(created_suites)}")
        print(f"  - Test Cases: {len(created_cases)}")
        print(f"  - Verification Runs: {len(created_runs)}")
        first_project_id = str(created_projects[0].id)
        print(f"Primary Project ID for Reports testing: {first_project_id}")
        return first_project_id

if __name__ == "__main__":
    seed()
