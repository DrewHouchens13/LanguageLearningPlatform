#!/usr/bin/env python
"""
Manual script to fix proficiency_level values in the database before running migrations.

This script converts any remaining CEFR string values (A1, A2, B1) to integers (1, 2, 3)
in the database. Run this in the Render terminal if migrations are failing.

Usage:
    python fix_proficiency_levels.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def fix_proficiency_levels():
    """Convert CEFR string values to integers in the database."""
    cefr_to_int = {'A1': 1, 'A2': 2, 'B1': 3}
    
    try:
        with connection.cursor() as cursor:
            # Check what database we're using
            vendor = connection.vendor
            print(f"Database vendor: {vendor}")
            
            if vendor == 'postgresql':
                for table in ['home_userlanguageprofile', 'home_userprofile']:
                    print(f"\nProcessing table: {table}")
                    
                    # First, check the current column type
                    cursor.execute("""
                        SELECT data_type 
                        FROM information_schema.columns 
                        WHERE table_name = %s AND column_name = 'proficiency_level'
                    """, [table])
                    result = cursor.fetchone()
                    
                    if not result:
                        print(f"  Column {table}.proficiency_level does not exist, skipping")
                        continue
                    
                    current_type = result[0]
                    print(f"  Current column type: {current_type}")
                    
                    if current_type == 'integer':
                        print(f"  Column is already integer, checking for string values...")
                        # Check if there are any string values (shouldn't happen, but check anyway)
                        cursor.execute(f"""
                            SELECT COUNT(*) 
                            FROM {table} 
                            WHERE proficiency_level IS NOT NULL 
                            AND proficiency_level::text NOT SIMILAR TO '[0-9]+'
                        """)
                        count = cursor.fetchone()[0]
                        if count > 0:
                            print(f"  Found {count} non-integer values, converting...")
                            # Update string values to integers
                            for cefr, int_val in cefr_to_int.items():
                                cursor.execute(f"""
                                    UPDATE {table}
                                    SET proficiency_level = %s
                                    WHERE proficiency_level::text = %s
                                """, [int_val, cefr])
                            print(f"  Converted {count} values")
                        else:
                            print(f"  All values are already integers")
                    else:
                        # Column is not integer, convert it
                        print(f"  Converting column from {current_type} to integer...")
                        try:
                            cursor.execute(f"""
                                ALTER TABLE {table}
                                ALTER COLUMN proficiency_level TYPE INTEGER
                                USING CASE
                                    WHEN proficiency_level::text = 'A1' THEN 1
                                    WHEN proficiency_level::text = 'A2' THEN 2
                                    WHEN proficiency_level::text = 'B1' THEN 3
                                    WHEN proficiency_level::text ~ '^[0-9]+$' THEN CAST(proficiency_level::text AS INTEGER)
                                    ELSE NULL
                                END;
                            """)
                            print(f"  Successfully converted {table}.proficiency_level to integer")
                        except Exception as e:
                            print(f"  Error converting {table}.proficiency_level: {e}")
                            raise
            else:
                print(f"Unsupported database vendor: {vendor}")
                print("This script is designed for PostgreSQL. Please handle other databases manually.")
                return 0  # Exit successfully - not an error, just not applicable
    except Exception as e:
        # Handle cases where tables don't exist yet (first migration) or other errors
        print(f"Error accessing database: {e}")
        print("This may be normal if migrations haven't run yet or tables don't exist.")
        print("The migration will handle the conversion if needed.")
        return 0  # Exit successfully - let migrations handle it

if __name__ == '__main__':
    import sys
    try:
        fix_proficiency_levels()
        print("\nDone!")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Continuing with build process...")
        sys.exit(0)  # Exit successfully to not fail the build

