# load dinesafe.csv to sqlite

import sqlite3
import pandas as pd

# Process matches
def process_matches(latitude, longitude, establishment_name, establishment_address, poi_rows):
    closest_match = None
    closest_score = 0
    for poi in poi_rows:
        # Calculate distance
        poi_lat = poi[1]
        poi_lon = poi[2]
        poi_housenumber = poi[5]
        poi_street = poi[6]
        if poi_housenumber is not None and poi_street is not None:
            poi_address = f"{poi_housenumber} {poi_street}".strip()
        else:
            poi_address = None
        # Calculate haversine distance
        distance = haversine(latitude, longitude, poi_lat, poi_lon)
        # calculate levenshtein distance for name
        poi_name = poi[0]
        name_levenshtein = levenshtein_percentage(establishment_name, poi_name)
        name_token_set_ratio = token_set_ratio(establishment_name, poi_name)
        name_distance = max(name_levenshtein, name_token_set_ratio)
        # calculate levenshtein distance for address
        if establishment_address and poi_address:
            address_distance = levenshtein_percentage(establishment_address, poi_address)
        else:
            address_distance = 0.0
        # Calculate score based on distance and name similarity
        score = (1 - distance / 100) * 0.3 + name_distance * 0.5 + address_distance * 0.2
        if closest_match is None or score > closest_score:
            closest_match = poi
            closest_score = score

    return closest_match, closest_score

# Calculate distance in km between two lat and lon points
def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2

    R = 6371.0  # Radius of the Earth in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def levenshtein(s1, s2):
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def levenshtein_percentage(s1, s2):
    """Calculate the Levenshtein distance as a percentage."""
    if not s1 and not s2:
        return 100.0
    if not s1 or not s2:
        return 0.0
    distance = levenshtein(s1.lower(), s2.lower())
    max_len = max(len(s1), len(s2))
    return (1 - distance / max_len) * 100

def token_set_ratio(s1, s2):
    """Calculate the token set ratio between two strings."""
    if not s1 and not s2:
        return 100.0
    if not s1 or not s2:
        return 0.0
    from rapidfuzz import fuzz
    return fuzz.token_set_ratio(s1.lower(), s2.lower())

dinesafe_file = 'dinesafe.csv'

conn = sqlite3.connect(':memory:')
dinesafe_df = pd.read_csv(dinesafe_file, encoding='utf-8')
# I only want the most recent value of [Inspection Date] for each [Establishment ID]
dinesafe_df = dinesafe_df.sort_values(by='Inspection Date').drop_duplicates(subset='Establishment ID', keep='last')
dinesafe_df.to_sql('dinesafe', conn, index=False)

# Load toronto_pois.csv
toronto_pois_file = 'toronto_pois.csv'
toronto_pois_df = pd.read_csv(toronto_pois_file, encoding='utf-8')

toronto_pois_df.to_sql('toronto_pois', conn, index=False)

matches = 0
no_matches = 0

# Iterate through each row in dinesafe using sqlite
cur = conn.cursor()
cur.execute("SELECT _id, latitude, longitude, [Establishment Name], [Establishment Address] FROM dinesafe")
while True:
    row = cur.fetchone()
    if row is None:
        break
    # Get _id column
    dinesafe_id = row[0]
    latitude = row[1]
    longitude = row[2]
    establishment_name = row[3]
    establishment_address = row[4]
    # Find the closest POI in toronto_pois
    cur2 = conn.cursor()
    cur2.execute("SELECT * FROM toronto_pois WHERE ABS(lat - ?) < 0.01 AND ABS(lon - ?) < 0.01", (latitude, longitude))
    poi_rows = cur2.fetchall()
    if poi_rows:
        closest_match, closest_score = process_matches(latitude, longitude, establishment_name, establishment_address, poi_rows)
        if closest_score >= 50:  # threshold for a good match
            print(f"Found POI for dinesafe ID {establishment_name} {establishment_address} at ({latitude}, {longitude}): {closest_match} with score {closest_score}".encode('cp1252', errors='replace').decode('cp1252'))
            matches += 1
        else:
            print(f"No good match found for dinesafe ID {establishment_name} {establishment_address} at ({latitude}, {longitude})".encode('cp1252', errors='replace').decode('cp1252'))
            no_matches += 1
    else:
        print(f"No POI found for dinesafe ID {dinesafe_id} at ({latitude}, {longitude})".encode('cp1252', errors='replace').decode('cp1252'))
        no_matches += 1

# Print summary
print(f"Total matches found: {matches}")
print(f"Total no matches found: {no_matches}")
print(f"Total dinesafe entries processed: {matches + no_matches}")
print(f"Total POIs in toronto_pois: {len(toronto_pois_df)}")
print(f"Match percentage: {matches / (matches + no_matches) * 100:.2f}%")

# close connection
conn.close()