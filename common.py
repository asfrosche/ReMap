import folium
import os
import logging
from typing import Dict, Tuple

def create_map(user_locations: Dict) -> Tuple[folium.Map, Dict]:
    # Create a world map centered at (0, 0) with zoom level 2 for world view
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Group users by country
    country_users = {}
    for user_id, data in user_locations.items():
        country = data['country']
        if country not in country_users:
            country_users[country] = []
        country_users[country].append({
            'name': data['name'],
            'avatar': data['avatar']
        })

        # Create custom HTML for the popup with user avatar and name
        popup_html = f"""
        <div style="text-align: center; padding: 10px;">
            <img src="{data['avatar'] or 'https://cdn.discordapp.com/embed/avatars/0.png'}" 
                 style="width: 48px; height: 48px; border-radius: 50%; margin-bottom: 5px;" 
                 onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <br>
            <strong>{data['name']}</strong>
            <br>
            {country}
        </div>
        """

        # Create custom icon with username
        icon_html = f'''
        <div style="text-align: center;">
            <img src="{data['avatar'] or 'https://cdn.discordapp.com/embed/avatars/0.png'}" 
                 style="width: 32px; height: 32px; border-radius: 50%;"
                 onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div style="font-size: 12px; font-weight: bold; background: rgba(0,0,0,0.7); 
                        color: white; padding: 2px 4px; border-radius: 3px; margin-top: 2px;">
                {data['name']}
            </div>
        </div>
        '''

        # Add marker with custom icon and popup
        folium.Marker(
            location=[data['lat'], data['lon']],
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=data['name'],
            icon=folium.DivIcon(html=icon_html, icon_size=(50, 50))
        ).add_to(m)

    return m, country_users

def get_continent(country: str) -> str:
    # Basic continent mapping - can be expanded
    continent_mapping = {
        'North America': ['United States', 'Canada', 'Mexico'],
        'South America': ['Brazil', 'Argentina', 'Chile', 'Peru', 'Colombia', 'Venezuela'],
        'Europe': ['United Kingdom', 'Germany', 'France', 'Italy', 'Spain', 'Poland', 'Romania'],
        'Asia': ['China', 'Japan', 'India', 'South Korea', 'Vietnam', 'Thailand', 'Indonesia'],
        'Africa': ['South Africa', 'Nigeria', 'Egypt', 'Kenya', 'Morocco', 'Ethiopia'],
        'Oceania': ['Australia', 'New Zealand', 'Fiji', 'Papua New Guinea']
    }

    for continent, countries in continent_mapping.items():
        if any(c.lower() in country.lower() for c in countries):
            return continent
    return "Other"