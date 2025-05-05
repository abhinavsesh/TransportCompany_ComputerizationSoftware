# Transport Company Computerization System (TCCS)

A structured software solution for automating consignment handling and fleet management for a nationwide transport company. Designed to improve truck utilization, automate billing, and provide management insights.

## 🚚 Features

- Branch-wise consignment entry with volume, sender/receiver, and destination details
- Automated billing based on volume and distance
- Automatic truck allotment when 500 m³ consignment volume is reached
- Real-time tracking of trucks (status: available, in transit, idle)
- Truck dispatch with printed consignment details
- Manager dashboard with queries on:
  - Truck status
  - Truck usage in a given time period
  - Consignment volume and revenue by destination
  - Average waiting time for consignments
  - Truck idle time for planning

## 🛠️ Technologies Used

- Python (Flask/Tkinter for UI)
- MySQL (backend data storage)
- Pandas (for reporting and analytics)
- Matplotlib (for visual insights – optional)

## 📂 Project Structure


## ✅ Getting Started

1. **Install dependencies**

2. **Set up MySQL**
- Create database and tables using `database.sql`.

3. **Run the app**

4. Open browser and visit: http://localhost:5000/

## 📈 Reporting Metrics

- Volume handled per destination
- Revenue generated
- Average consignment waiting time
- Truck idle time in branches
- Truck usage over selected date ranges

## 🧪 Testing

Manual and logic-based validation was performed for:
- Threshold volume-based truck assignment
- Consignment readiness tracking
- Data integrity for billing and queries

## 📌 Future Enhancements

- Add role-based login (manager, operator)
- Visual dashboards for analytics
- SMS/email dispatch notifications
- Truck route optimization algorithms

## 📄 License

This project is open-source under the MIT License.
