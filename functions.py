import requests
from datetime import datetime, timedelta

AIRTABLE_API_KEY = 'pats73zHAV5ewFaQu.1bef3c9d7d154ec90f6bd2e3ffcae59c7a1130bfd087ec78323a9913e43260a7'
AIRTABLE_BASE_ID = 'appIwbngRFs1mUfGt'
AIRTABLE_TABLES_URL = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Tables'
AIRTABLE_RESERVATIONS_URL = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Reservations'
HEADERS = {'Authorization': f'Bearer {AIRTABLE_API_KEY}'}

def get_standard_duration(number_of_guests):
    if number_of_guests <= 4:
        return 1.5  # Duration for 2-4 people
    elif number_of_guests <= 6:
        return 2    # Duration for 5-6 people
    else:
        return 2.5  # Duration for 7+ people

def check_availability_and_reserve(number_of_guests, reservation_start):
    print(reservation_start)
    reservation_start = datetime.strptime(reservation_start, '%Y-%m-%dT%H:%M:%S')
    duration = get_standard_duration(number_of_guests)
    reservation_end = reservation_start + timedelta(hours=duration)

    # Fetch all tables
    tables = requests.get(AIRTABLE_TABLES_URL, headers=HEADERS).json()

    sorted_tables = sorted(tables.get('records', []), key=lambda x: x['fields']['TableSize'])

    suitable_table = None
    for record in sorted_tables:
        table_id = record['fields']['TableID']
        table_size = record['fields']['TableSize']

        # Skip table if it can't seat the required number of guests
        if table_size < number_of_guests:
            continue

        # Check existing reservations for the table
        reservations = requests.get(
            AIRTABLE_RESERVATIONS_URL,
            headers=HEADERS,
            params={"filterByFormula": f"TableID = '{table_id}'"}
        ).json()

        is_available = not any(
            (datetime.strptime(res['fields']['ReservationStart'], '%Y-%m-%dT%H:%M:%S') < reservation_end and
             datetime.strptime(res['fields']['ReservationEnd'], '%Y-%m-%dT%H:%M:%S') > reservation_start)
            for res in reservations.get('records', [])
        )

        # Check if table is available for the entire desired reservation period
        if is_available:
            suitable_table = table_id
            print(suitable_table)
            break

    if suitable_table:
        print("make reservation")
        # Make reservation
        data = {
            "fields": {
                "TableID": suitable_table,
                "NumberOfGuests": number_of_guests,
                "ReservationStart": reservation_start.strftime('%Y-%m-%dT%H:%M:%S'),
                "ReservationEnd": reservation_end.strftime('%Y-%m-%dT%H:%M:%S')
            }
        }
        response = requests.post(AIRTABLE_RESERVATIONS_URL, headers=HEADERS, json=data)
        print(response.content)
        return response.status_code == 200
    else:
        # No available table
        return False

check_availability_and_reserve(9, "2023-11-10T20:00:00")
