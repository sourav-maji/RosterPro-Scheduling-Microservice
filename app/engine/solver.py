from ortools.sat.python import cp_model
from collections import defaultdict


def solve_weekly_schedule(payload, max_time=20):
    """
    Weekly scheduler with:
    - Partial coverage support
    - Coverage minimization
    - Shift fairness
    - Night fairness
    - Consecutive night prevention
    """

    input_data = payload
    model = cp_model.CpModel()

    DAYS = list(range(len(input_data.days)))
    SHIFT_NAMES = list(input_data.shifts.keys())

    staff_ids = [s.id for s in input_data.staff]
    roles = {s.id: s.role for s in input_data.staff}

    # -------------------------------------------------
    # Decision Variables
    # x[user, day, shift] ∈ {0,1}
    # -------------------------------------------------
    x = {}
    for u in staff_ids:
        for d in DAYS:
            for s in SHIFT_NAMES:
                x[(u, d, s)] = model.NewBoolVar(f"x_{u}_{d}_{s}")

    # -------------------------------------------------
    # UNMET DEMAND VARIABLES
    # unmet[day, shift, role] ≥ 0
    # -------------------------------------------------
    unmet = {}
    for d in DAYS:
        for shift, role_map in input_data.requirements.items():
            for role, required in role_map.items():
                unmet[(d, shift, role)] = model.NewIntVar(
                    0, required, f"unmet_{d}_{shift}_{role}"
                )

    # -------------------------------------------------
    # HARD CONSTRAINTS
    # -------------------------------------------------

    # 1️⃣ One shift per user per day
    for u in staff_ids:
        for d in DAYS:
            model.Add(sum(x[(u, d, s)] for s in SHIFT_NAMES) <= 1)

    # 2️⃣ Role coverage (PARTIAL allowed)
    for d in DAYS:
        for shift, role_map in input_data.requirements.items():
            for role, required in role_map.items():
                model.Add(
                    sum(
                        x[(u, d, shift)]
                        for u in staff_ids
                        if roles[u] == role
                    ) + unmet[(d, shift, role)]
                    == required
                )

    # 3️⃣ Max shifts per week
    for u in staff_ids:
        limit = input_data.max_shifts_per_week.get(roles[u])
        if limit is not None:
            model.Add(
                sum(x[(u, d, s)] for d in DAYS for s in SHIFT_NAMES) <= limit
            )

    # 4️⃣ Max weekly hours
    for u in staff_ids:
        hour_limit = input_data.max_weekly_hours.get(roles[u])
        if hour_limit is not None:
            model.Add(
                sum(
                    x[(u, d, s)] * input_data.shifts[s]
                    for d in DAYS
                    for s in SHIFT_NAMES
                ) <= hour_limit
            )

    # 5️⃣ STEP 5 — NO CONSECUTIVE NIGHT SHIFTS (HARD)
    for u in staff_ids:
        for d in range(len(DAYS) - 1):
            if "Night" in SHIFT_NAMES:
                model.Add(
                    x[(u, d, "Night")] + x[(u, d + 1, "Night")] <= 1
                )

    # -------------------------------------------------
    # STEP 4 — SECONDARY OBJECTIVES (FAIRNESS)
    # -------------------------------------------------

    # Average shifts per role
    avg_shifts = {}
    for role in set(roles.values()):
        users = [u for u in staff_ids if roles[u] == role]
        avg_shifts[role] = len(DAYS) / max(len(users), 1)

    # Shift deviation
    shift_dev = {}
    for u in staff_ids:
        shift_dev[u] = model.NewIntVar(0, len(DAYS), f"shift_dev_{u}")
        total_shifts = sum(x[(u, d, s)] for d in DAYS for s in SHIFT_NAMES)

        model.Add(shift_dev[u] >= total_shifts - int(avg_shifts[roles[u]]))
        model.Add(shift_dev[u] >= int(avg_shifts[roles[u]]) - total_shifts)

    # Night shift deviation
    night_dev = {}
    for u in staff_ids:
        night_dev[u] = model.NewIntVar(0, len(DAYS), f"night_dev_{u}")
        model.Add(
            night_dev[u] >=
            sum(x[(u, d, s)] for d in DAYS for s in SHIFT_NAMES if s.lower() == "night")
        )

    # -------------------------------------------------
    # OBJECTIVE (PRIORITIZED)
    # -------------------------------------------------
    model.Minimize(
        1000 * sum(unmet.values()) +
        10 * sum(shift_dev.values()) +
        5 * sum(night_dev.values())
    )

    # -------------------------------------------------
    # SOLVE
    # -------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = min(max_time, 5)
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    # -------------------------------------------------
    # BUILD RESPONSE
    # -------------------------------------------------
    schedule = []
    summary = defaultdict(lambda: {
        "totalShifts": 0,
        "nightShifts": 0
    })

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for d_idx, day_name in enumerate(input_data.days):
            day_entry = {"day": day_name, "shifts": {}}

            for s in SHIFT_NAMES:
                assigned = []
                for u in staff_ids:
                    if solver.Value(x[(u, d_idx, s)]) == 1:
                        assigned.append(u)
                        summary[u]["totalShifts"] += 1
                        if s.lower() == "night":
                            summary[u]["nightShifts"] += 1

                day_entry["shifts"][s] = assigned

            schedule.append(day_entry)

        return {
            "status": "SUCCESS" if status == cp_model.OPTIMAL else "PARTIAL",
            "schedule": schedule,
            "summary": [
                {
                    "userId": u,
                    "role": roles[u],
                    **summary[u]
                }
                for u in summary
            ],
            "violations": {
                "unmetDemand": {
                    f"{input_data.days[d]}-{shift}-{role}": solver.Value(v)
                    for (d, shift, role), v in unmet.items()
                    if solver.Value(v) > 0
                }
            }
        }

    return {
        "status": "FAILED",
        "message": "No feasible schedule found"
    }
