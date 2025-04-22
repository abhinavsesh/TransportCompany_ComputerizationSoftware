
# analytics.py
import database_manager as db
from models import Branch, Consignment, Truck # Import necessary models
from datetime import datetime, timedelta, date, timezone
import calendar

def calculate_average_waiting_time():
    """Calculates the average waiting time of all consignments in hours."""
    consignments = db.get_all_consignments() # Assumes this function exists in db manager
    if not consignments:
        return 0.0

    total_waiting_hours = 0.0
    valid_count = 0
    for c in consignments:
        if c.created_at: # Ensure creation time exists
            total_waiting_hours += c.get_waiting_time_hours() # Use model method
            valid_count += 1

    return total_waiting_hours / valid_count if valid_count > 0 else 0.0

def calculate_average_truck_idle_time():
    """Calculates the average idle time of AVAILABLE trucks in hours."""
    trucks = db.get_all_trucks() # Assumes this function exists
    if not trucks:
        return 0.0

    total_idle_hours = 0.0
    idle_truck_count = 0
    now = datetime.now(timezone.utc) # Use timezone-aware comparison

    for truck in trucks:
        if truck.status == 'AVAILABLE' and truck.idle_since:
            idle_start = truck.idle_since
            # Make idle_start timezone-aware if it's naive (assume UTC)
            if idle_start.tzinfo is None:
                idle_start = idle_start.replace(tzinfo=timezone.utc)

            idle_duration = now - idle_start
            if idle_duration.total_seconds() > 0:
                total_idle_hours += idle_duration.total_seconds() / 3600.0
                idle_truck_count += 1

    return total_idle_hours / idle_truck_count if idle_truck_count > 0 else 0.0


def _get_first_day_of_month(dt):
    return dt.replace(day=1)

def _get_last_day_of_month(dt):
    _, last_day = calendar.monthrange(dt.year, dt.month)
    return dt.replace(day=last_day)

def generate_revenue_report():
    """Generates a detailed text-based revenue report."""
    report = []
    now = datetime.now()
    branches = db.get_all_branches()
    total_revenue = db.get_total_revenue()

    report.append("==================== REVENUE REPORT ====================")
    report.append(f"Generated on: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"Total Overall Revenue: Rs. {total_revenue:.2f}")
    report.append("------------------------------------------------------")
    report.append("Branch-wise Revenue Breakdown:")
    report.append("------------------------------------------------------")

    if not branches:
        report.append("  No branches found.")
    else:
        for branch in branches:
            branch_revenue = db.get_total_revenue_by_branch(branch.branch_id)
            percentage = (branch_revenue / total_revenue * 100) if total_revenue > 0 else 0
            report.append(f" {branch.name:<15s} ({branch.branch_id}): Rs. {branch_revenue:<15.2f} ({percentage:5.1f}%)")

    report.append("\n------------------------------------------------------")
    report.append("Monthly Revenue (Last 6 Months):")
    report.append("------------------------------------------------------")

    current_date = date.today()
    for i in range(6):
        # Calculate start and end date for the month
        target_date = current_date - timedelta(days=sum(calendar.monthrange(current_date.year if current_date.month - j > 0 else current_date.year-1, (current_date.month - j -1)%12+1)[1] for j in range(i))) # Approx logic, better use relativedelta or careful calcs
        start_date = _get_first_day_of_month(target_date)
        end_date = _get_last_day_of_month(target_date)

        monthly_revenue = db.get_revenue_by_period(start_date, end_date)

        month_str = start_date.strftime("%B %Y")
        report.append(f" {month_str:<15s} ({start_date} to {end_date}): Rs. {monthly_revenue:.2f}")


    report.append("================== END OF REVENUE REPORT =================")
    return "\n".join(report)


def generate_analytics_summary():
    """Generates a general analytics summary text."""
    summary = []
    now = datetime.now()

    summary.append("================== ANALYTICS SUMMARY ==================")
    summary.append(f"Generated on: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Consignment Metrics
    all_consignments = db.get_all_consignments()
    pending_count = sum(1 for c in all_consignments if c.status == 'PENDING')
    in_transit_count = sum(1 for c in all_consignments if c.status == 'IN_TRANSIT')
    delivered_count = sum(1 for c in all_consignments if c.status == 'DELIVERED')
    avg_waiting_time = calculate_average_waiting_time()

    summary.append("--- Consignments ---")
    summary.append(f" Total Consignments: {len(all_consignments)}")
    summary.append(f"   - Pending:    {pending_count}")
    summary.append(f"   - In Transit: {in_transit_count}")
    summary.append(f"   - Delivered:  {delivered_count}")
    summary.append(f" Average Waiting Time (All): {avg_waiting_time:.2f} hours\n")

    # Truck Metrics
    all_trucks = db.get_all_trucks()
    available_trucks = sum(1 for t in all_trucks if t.status == 'AVAILABLE')
    transit_trucks = sum(1 for t in all_trucks if t.status == 'IN_TRANSIT')
    maintenance_trucks = sum(1 for t in all_trucks if t.status == 'MAINTENANCE')
    avg_idle_time = calculate_average_truck_idle_time()

    summary.append("--- Fleet (Trucks) ---")
    summary.append(f" Total Trucks: {len(all_trucks)}")
    summary.append(f"   - Available:   {available_trucks}")
    summary.append(f"   - In Transit:  {transit_trucks}")
    summary.append(f"   - Maintenance: {maintenance_trucks}")
    summary.append(f" Average Idle Time (Available Trucks): {avg_idle_time:.2f} hours\n")

    # Financial Metrics
    total_revenue = db.get_total_revenue()
    summary.append("--- Financials ---")
    summary.append(f" Total Recorded Revenue: Rs. {total_revenue:.2f}")
    summary.append("   (Expense tracking not implemented)")

    summary.append("================ END OF ANALYTICS SUMMARY ================")
    return "\n".join(summary)