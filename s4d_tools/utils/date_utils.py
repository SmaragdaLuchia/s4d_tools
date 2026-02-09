"""
Utility functions for StanForD parsers
"""
from datetime import datetime


def format_date(date_str):
    if not date_str:
        return ''
    
    # Try ISO format first (contains 'T' or '-' separators)
    if 'T' in date_str or (len(date_str) > 10 and '-' in date_str[:10]):
        try:
            # Handle timezone by replacing Z with +00:00 for fromisoformat
            date_str_clean = date_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(date_str_clean)
            return dt.strftime('%d-%m-%Y %H:%M')
        except (ValueError, AttributeError):
            # If ISO parsing fails, try YYYYMMDDHHMMSS format
            pass
    
    # Try YYYYMMDDHHMMSS format 
    if len(date_str) >= 14 and date_str.replace(' ', '').isdigit():
        try:
            # Remove any spaces and take first 14 characters
            date_clean = date_str.replace(' ', '')[:14]
            if len(date_clean) == 14:
                year = date_clean[0:4]
                month = date_clean[4:6]
                day = date_clean[6:8]
                hour = date_clean[8:10]
                minute = date_clean[10:12]
                
                # Validate the date components
                datetime(int(year), int(month), int(day), int(hour), int(minute))
                
                # Format as DD-MM-YYYY HH:MM
                return f"{day}-{month}-{year} {hour}:{minute}"
        except (ValueError, IndexError):
            pass
    
    # If all parsing fails, return original string
    return date_str
