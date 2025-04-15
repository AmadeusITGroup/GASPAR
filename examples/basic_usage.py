"""
Basic usage example for GASPAR system.
"""

import asyncio
import random
from datetime import datetime, timedelta, date
from typing import Dict, Any, AsyncIterator, List
from gaspar.config import load_config
from gaspar.pipeline.executor import PipelineExecutor

def generate_sample_data(num_records: int = 1000) -> List[Dict[str, Any]]:
    """
    Generate sample data records matching IPA fields.

    Args:
        num_records: Number of records to generate

    Returns:
        List of sample data records
    """
    # Normal data patterns
    full_names = [
        "John Robert Smith", "Emma Grace Wilson", "Michael James Brown",
        "Sarah Elizabeth Davis", "James William Johnson", "Emily Marie Anderson",
        "William Thomas Taylor", "Olivia Rose Thomas", "Alexander David White",
        "Sophia Isabella Martinez", "Daniel Richard Lee", "Isabella Maria Garcia",
        "David Michael Miller", "Mia Catherine Rodriguez", "Joseph Andrew Wilson",
        "Charlotte Anne Moore"
    ]

    domains = ["example.com", "company.com", "mail.com", "business.org", "corp.net"]

    street_names = [
        "Main Street", "Oak Avenue", "Maple Drive", "Cedar Lane", "Pine Road",
        "Elm Street", "Washington Avenue", "Park Road", "Lake Drive", "Hill Street"
    ]

    cities = [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
        "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"
    ]

    states = [
        "NY", "CA", "IL", "TX", "AZ", "PA", "FL", "OH", "GA", "NC"
    ]

    bank_names = [
        "Chase", "Bank of America", "Wells Fargo", "Citibank", "Capital One",
        "US Bank", "PNC Bank", "TD Bank", "BB&T", "SunTrust"
    ]

    data_owners = ["AI", "AY", "AF", "AC", "1A", "BA", "BR", "CA", "CX", "DA", "KL", "LH", "MH",
                   "TG", "XY", "ZA"]

    data_processors = ["AI", "AY", "AF", "AC", "1A", "BA", "BR", "CA", "CX", "DA", "KL", "LH", "MH",
                   "TG", "XY", "ZA"]

    def generate_phone():
        return f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"

    def generate_address():
        return (f"{random.randint(100, 9999)} {random.choice(street_names)}, "
                f"{random.choice(cities)}, {random.choice(states)} "
                f"{random.randint(10000, 99999)}")

    def generate_dob():
        start_date = date(1950, 1, 1)
        end_date = date(2005, 12, 31)
        days_between = (end_date - start_date).days
        random_days = random.randint(0, days_between)
        return (start_date + timedelta(days=random_days)).isoformat()

    def generate_ssn():
        return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"

    def generate_banking_info():
        bank = random.choice(bank_names)
        routing = f"{random.randint(100000000, 999999999)}"
        account = f"{random.randint(10000000, 99999999)}"
        return {
            "bank_name": bank,
            "routing_number": routing,
            "account_number": account
        }

    def generate_data_owner():
        return random.choice(data_owners)

    def generate_data_processor():
        return random.choice(data_processors)

    # Generate base data
    data = []
    for _ in range(num_records):
        # Generate normal record
        full_name = random.choice(full_names)
        email = f"{full_name.lower().replace(' ', '.')}@{random.choice(domains)}"

        record = {
            "Full Name": full_name,
            "Email Address": email,
            "Phone Number": generate_phone() if random.random() < 0.7 else None,  # Optional
            "Physical Address": generate_address() if random.random() < 0.6 else None,  # Optional
            "Date of Birth": generate_dob(),
            "Social Security Number": generate_ssn(),
            "Banking Information": generate_banking_info() if random.random() < 0.4 else None,  # Optional
            "timestamp": (datetime.now() + timedelta(minutes=random.randint(0, 60))).isoformat(),
            "Data Owner": generate_data_owner(),
            "Data Processor": generate_data_processor()
        }

        # Introduce anomalies (roughly 10% of records)
        if random.random() < 0.1:
            anomaly_type = random.random()

            if anomaly_type < 0.2:
                # Invalid email format
                record["Email Address"] = f"{full_name.lower().replace(' ', '.')}.invalid"
            elif anomaly_type < 0.4:
                # Invalid date of birth (future date)
                record["Date of Birth"] = (date.today() + timedelta(days=random.randint(1, 365))).isoformat()
            elif anomaly_type < 0.6:
                # Invalid SSN format
                record["Social Security Number"] = f"{random.randint(1000, 9999)}"
            elif anomaly_type < 0.7:
                # Invalid name format
                record["Full Name"] = f"{full_name}123"
            elif anomaly_type < 0.8:
                # Missing required field
                del record["Email Address"]
            elif anomaly_type < 0.9:
                # Invalid phone format
                record["Phone Number"] = f"{random.randint(100, 999)}"
            else:
                # Multiple anomalies
                record["Date of Birth"] = (date.today() + timedelta(days=random.randint(1, 365))).isoformat()
                record["Social Security Number"] = f"{random.randint(1000, 9999)}"

        data.append(record)

        # Add some systematic anomalies
        systematic_anomalies = []
        for _ in range(int(num_records * 0.05)):  # 5% additional systematic anomalies
            base_record = random.choice(data).copy()

            # Create systematic pattern
            if random.random() < 0.3:
                # Pattern: Invalid email domain
                if "Email Address" in base_record and "@" in base_record["Email Address"]:
                    try:
                        base_record["Email Address"] = base_record["Email Address"].replace(
                            "@" + base_record["Email Address"].split("@")[1],
                            "@suspicious.domain"
                        )
                    except IndexError:
                        base_record["Email Address"] = "invalid@suspicious.domain"
            elif random.random() < 0.6:
                # Pattern: Banking info for specific names
                if "Smith" in base_record.get("full_name", ""):
                    base_record["Banking Information"] = {
                        "bank_name": "Suspicious Bank",
                        "routing_number": "000000000",
                        "account_number": "00000000"
                    }
            else:
                # Pattern: Invalid addresses for specific cities
                physical_address = base_record.get("physical_address", "")
                if physical_address and "New York" in physical_address:
                    base_record["physical_address"] = "Invalid Address"

            systematic_anomalies.append(base_record)

    # Add time-based anomalies
    time_based_anomalies = []
    anomaly_time = datetime.now() + timedelta(minutes=30)  # Cluster around 30 minutes in
    for _ in range(int(num_records * 0.03)):  # 3% time-based anomalies
        base_record = random.choice(data).copy()
        base_record["timestamp"] = (
            anomaly_time + timedelta(minutes=random.randint(-5, 5))
        ).isoformat()

        # Create suspicious pattern during specific time window
        base_record["Banking Information"] = {
            "bank_name": "Offshore Bank",
            "routing_number": "999999999",
            "account_number": "99999999"
        }
        base_record["physical_address"] = "Undisclosed Location"
        time_based_anomalies.append(base_record)

    # Combine all data
    all_data = data + systematic_anomalies + time_based_anomalies
    # Sort by timestamp
    all_data.sort(key=lambda x: x["timestamp"])

    return all_data

async def sample_data_feed() -> AsyncIterator[Dict[str, Any]]:
    """
    Example data feed generator.
    Simulates a real-time data feed with normal patterns and anomalies.
    """
    # Generate sample data
    data = generate_sample_data(1000)

    # Stream the data
    for record in data:
        yield record
        await asyncio.sleep(0.1)  # Simulate real-time data feed

async def handle_violations(violations: list) -> None:
    """
    Handle detected privacy violations.

    Args:
        violations: List of detected violations
    """
    print("\nPrivacy violations detected:")
    for violation in violations:
        print(f"\nField: {violation.field_name}")
        print(f"Value: {violation.actual_value}")
        print(f"Type: {violation.violation_type}")
        print(f"Severity: {violation.severity}")
        print(f"Confidence: {violation.confidence:.2f}")

        if violation.distribution_metrics:
            print("Distribution Analysis:")
            for metric, value in violation.distribution_metrics.items():
                print(f"- {metric}: {value}")

async def handle_batch(batch: list) -> None:
    """
    Process data batch after distribution update.

    Args:
        batch: List of processed data samples
    """
    print(f"\nProcessed batch of {len(batch)} records")
    # You can add additional batch processing logic here

async def main():
    try:
        # Load configuration
        config = load_config("config.yaml")

        # Initialize pipeline executor
        executor = PipelineExecutor(config)

        # Get some initial data for baseline distribution modeling
        print("Collecting initial data for baseline modeling...")
        initial_data = []
        async for record in sample_data_feed():
            initial_data.append(record)
            if len(initial_data) >= 300:  # Collect 300 records for initial modeling
                break

        # Process IPA document and set up monitoring
        print("\nProcessing IPA document and initializing monitoring...")
        result = await executor.execute(
            r"C:\Users\mboustala\PycharmProjects\Gaspar\examples\documents\privacy_assessment.txt",
            initial_data=initial_data
        )
        #print("final result",result)

        if result:
            print("\nPipeline Setup Results:")
            if "privacy_rules" in result.state:
                print("\nPrivacy Rules Extracted:")
                for rule in result.state["privacy_rules"]:
                    print(f"- {rule.field_name}: {rule.privacy_level}")
                    if not rule.allowed:
                        print("  Not Allowed")
                    if rule.constraints:
                        print(f"  Constraints: {rule.constraints}")

            print("\nGenerated Artifacts:")
            for name, path in result.artifacts.items():
                print(f"- {name}: {path}")

        #     # Start monitoring data feed
        #     print("\nStarting data monitoring...")
        #     monitor_task = asyncio.create_task(
        #         executor.monitor_data_source(
        #             sample_data_feed(),
        #             violation_callback=handle_violations,
        #             #batch_processor=handle_batch
        #         )
        #     )
        #
        #     # Let monitoring run for a while
        #     print("\nMonitoring data feed for 60 seconds...")
        #     await asyncio.sleep(60)
        #
        #     # Get monitoring stats
        #     stats = await executor.get_monitoring_stats()
        #     print("monitoring stats",stats)
        #     print("\nMonitoring Statistics:")
        #     print(f"Total Records: {stats['total_records']}")
        #     print(f"Sampled Records: {stats['sampled_records']}")
        #     print(f"Violations Detected: {stats['violation_count']}")
        #     print(f"Current Sampling Rate: {stats['current_sampling_rate']:.2%}")
        #     print(f"Distribution Updates: {stats['distribution_updates']}")
        #
        #     if 'field_distributions' in stats:
        #         print("\nField Distributions:")
        #         for field, dist in stats['field_distributions'].items():
        #             print(f"\n{field}:")
        #             if dist.get('mean') is not None:
        #                 print(f"- Mean: {dist['mean']:.2f}")
        #                 print(f"- Std Dev: {dist['std']:.2f}")
        #             if dist.get('categorical_counts'):
        #                 print(f"- Value Counts: {dist['categorical_counts']}")
        #
        #     # Get deployment status
        #     if hasattr(executor.steps[-1], 'get_quarantine_stats'):
        #         quarantine_stats = await executor.steps[-1].get_quarantine_stats()
        #         print("\nQuarantine Statistics:")
        #         print(f"Total Quarantined: {quarantine_stats['total_quarantined']}")
        #         print(f"Active Filters: {quarantine_stats['active_filters']}")
        #
        #         if quarantine_stats['filter_stats']:
        #             print("\nFilter Performance:")
        #             for filter_name, stats in quarantine_stats['filter_stats'].items():
        #                 print(f"\n{filter_name}:")
        #                 print(f"- Matches: {stats['count']}")
        #                 print(f"- Last Match: {stats['last_match']}")
        #
        #     # Stop monitoring
        #     print("\nStopping monitoring...")
        #     await executor.stop_monitoring()
        #     await monitor_task
        #
        # else:
        #     print("Pipeline execution failed!")
        #     if result:
        #         print(f"Error: {result.error_message}")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())