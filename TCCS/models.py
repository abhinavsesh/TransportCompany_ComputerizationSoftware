
# models.py
from dataclasses import dataclass, field
from datetime import datetime, date, timezone, timedelta
import math

# Using dataclasses for simplicity (similar to Java records/beans)

@dataclass
class User:
    user_id: str
    name: str
    role: str # 'MANAGER' or 'EMPLOYEE'
    branch_id: str
    contact: str = None
    address: str = None
    # password hash is not stored in the model instance after retrieval

    def is_manager(self) -> bool:
        return self.role and self.role.upper() == 'MANAGER'

    def __str__(self):
        return f"{self.name} ({self.user_id})"

@dataclass
class Branch:
    branch_id: str
    name: str
    location: str
    contact: str = None
    address: str = None

    def __str__(self):
        # Used for display in Comboboxes
        return f"{self.branch_id} - {self.name}"

@dataclass
class Truck:
    truck_id: str
    registration_no: str
    capacity: float
    status: str # 'AVAILABLE', 'IN_TRANSIT', 'MAINTENANCE'
    source_branch: str # Current base/location
    driver_name: str = None
    driver_contact: str = None
    current_location: str = None # Description, ideally matches source_branch location
    destination_branch: str = None # Only if IN_TRANSIT
    idle_since: datetime = None # Timestamp it became AVAILABLE

    def __str__(self):
         # Used for display in Comboboxes/Lists
        return f"{self.truck_id} - {self.registration_no} ({self.capacity} m³)"

@dataclass
class Consignment:
    consignment_id: str
    volume: float
    weight: float
    type: str
    sender_name: str
    sender_address: str
    sender_contact: str
    sender_id: str
    receiver_name: str
    receiver_address: str
    receiver_contact: str
    receiver_id: str
    source_branch: str
    destination_branch: str
    status: str # 'PENDING', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED'
    charges: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc)) # Default to now
    description: str = None
    truck_id: str = None # Assigned when loaded
    delivered_at: datetime = None

    def get_waiting_time_hours(self) -> float:
        """Calculates waiting time in hours from creation until now or delivery."""
        if not self.created_at:
            return 0.0

        # Ensure created_at is offset-aware (assuming UTC storage or conversion)
        start_time = self.created_at
        if start_time.tzinfo is None:
             # If naive, assume UTC (adjust if your DB stores local time)
             start_time = start_time.replace(tzinfo=timezone.utc)

        # Determine end time
        if self.status == 'DELIVERED' and self.delivered_at:
            end_time = self.delivered_at
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
        else:
            end_time = datetime.now(timezone.utc) # Current time

        duration = end_time - start_time
        return duration.total_seconds() / 3600.0 # Convert to hours

    def generate_receipt(self) -> str:
        """Generates a formatted text receipt for the consignment."""
        # Use local time for receipt display? Convert from UTC.
        local_tz = datetime.now().astimezone().tzinfo # Get local timezone
        created_str = self.created_at.astimezone(local_tz).strftime('%d-%m-%Y %H:%M:%S') if self.created_at else "N/A"
        delivered_str = self.delivered_at.astimezone(local_tz).strftime('%d-%m-%Y %H:%M:%S') if self.delivered_at else "-"

        receipt = []
        sep = "=" * 40 + "\n"
        line = "-" * 40 + "\n"
        receipt.append(sep)
        receipt.append("       TRANSPORT COMPANY RECEIPT        \n")
        receipt.append(sep)
        receipt.append(f"Consignment ID: {self.consignment_id:<20s}\n")
        receipt.append(f"Date Created:   {created_str:<20s}\n")
        receipt.append(line)
        receipt.append(" SENDER DETAILS\n")
        receipt.append(f" Name:    {self.sender_name:<25s}\n")
        receipt.append(f" Address: {self.sender_address:<25s}\n")
        receipt.append(f" Contact: {self.sender_contact:<25s}\n")
        receipt.append(f" ID Ref:  {self.sender_id:<25s}\n")
        receipt.append(line)
        receipt.append(" RECEIVER DETAILS\n")
        receipt.append(f" Name:    {self.receiver_name:<25s}\n")
        receipt.append(f" Address: {self.receiver_address:<25s}\n")
        receipt.append(f" Contact: {self.receiver_contact:<25s}\n")
        receipt.append(f" ID Ref:  {self.receiver_id:<25s}\n")
        receipt.append(line)
        receipt.append(" CONSIGNMENT INFO\n")
        receipt.append(f" Type:        {self.type:<20s}\n")
        receipt.append(f" Volume:      {self.volume:.2f} m³\n")
        receipt.append(f" Weight:      {self.weight:.2f} kg\n")
        if self.description:
            receipt.append(f" Description: {self.description:<20s}\n")
        receipt.append(f" CHARGES:     Rs. {self.charges:.2f}\n")
        receipt.append(line)
        receipt.append(" ROUTING & STATUS\n")
        receipt.append(f" Source:      {self.source_branch:<20s}\n")
        receipt.append(f" Destination: {self.destination_branch:<20s}\n")
        receipt.append(f" Status:      {self.status:<20s}\n")
        if self.truck_id:
            receipt.append(f" Truck ID:    {self.truck_id:<20s}\n")
        if self.status == 'DELIVERED' and self.delivered_at:
            receipt.append(f" Delivered At:{delivered_str:<20s}\n")
        receipt.append(sep)
        receipt.append("      Thank you for your business!      \n")
        receipt.append(sep)

        return "".join(receipt)

    @staticmethod
    def calculate_charges(volume: float, weight: float, source_branch: str, destination_branch: str) -> float:
        """Calculates consignment charges based on volume, weight, and distance factor."""
        # Constants (could be externalized)
        rate_per_cubic_meter = 1200.0
        rate_per_kg = 15.0
        base_charge = 600.0
        distance_multiplier = 1.0

        # Simplified distance factor
        if source_branch != destination_branch:
            distance_multiplier = 1.6
        else: # Local delivery
            distance_multiplier = 0.8
            base_charge = 300.0

        volume_charge = volume * rate_per_cubic_meter
        weight_charge = weight * rate_per_kg

        calculated_charge = max(volume_charge, weight_charge) * distance_multiplier
        final_charge = max(calculated_charge, base_charge)

        # Round to 2 decimal places
        return round(final_charge, 2)


@dataclass
class Revenue:
    transaction_id: int
    branch_id: str
    amount: float
    transaction_date: date # Use datetime.date
    description: str = None
    consignment_id: str = None

    def __str__(self):
        return f"Txn {self.transaction_id} [{self.transaction_date}] - Br: {self.branch_id}, Amt: {self.amount:.2f}"