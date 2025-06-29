import streamlit as st
import pandas as pd
import plotly.express as px

import clean

# Load the cleaned data
@st.cache_data
def load_and_summarize():
    df = pd.read_csv('vote_data_whitelisted_cleaned.csv')
    return df, clean.summarize_vote_data(df)

df_wl, df_maps = load_and_summarize()

st.set_page_config(layout="wide", page_title="Overwatch Map Voting Data", page_icon="favicon.png")

# Table of contents
st.sidebar.title("Views")
st.sidebar.markdown("""
[Title](#overwatch-map-voting-data)

[Map Tier List](#map-tier-list-based-on-votes-per-appearance)

[Bar Charts](#bar-charts)

[Votes by Card](#votes-by-card)

[Map Data](#map-data)

[Raw Data](#raw-data)

[Methodology](#methodology)
""")

left, center, right = st.columns([1, 5, 1])
with center:

    # --- TITLE ---
    st.title("Overwatch Map Voting Data")
    st.write("Data on Map Voting in Grandmaster, NA + EMEA Lobbies, extracted from public Twitch VODs.")
    st.write("Updated as of 2025-06-26.")

    # --- TIER LIST ---
    map_image_filenames = {
        "AATLIS": "map_images/Aatlis.jpg",
        "ANTARCTIC PENINSULA": "map_images/Antarctic_Peninsula.jpg",
        "BLIZZARD WORLD": "map_images/Blizzard-world.jpg",
        "CIRCUIT ROYAL": "map_images/Circuit_Royal.png",
        "BUSAN": "map_images/Busan.jpg",
        "COLOSSEO": "map_images/Colosseo.jpg",
        "DORADO": "map_images/Dorado.jpg",
        "EICHENWALDE": "map_images/Eichenwalde.jpg",
        "ESPERANÇA": "map_images/Esperanca.jpg",
        "HAVANA": "map_images/Havana.jpg",
        "HOLLYWOOD": "map_images/Hollywood.jpg",
        "ILIOS": "map_images/Ilios.jpg",
        "JUNKERTOWN": "map_images/Junkertown.jpg",
        "KING'S ROW": "map_images/Kings-row.jpg",
        "LIJIANG TOWER": "map_images/Lijiang-tower.jpg",
        "MIDTOWN": "map_images/Midtown.jpg",
        "NEPAL": "map_images/Nepal.jpg",
        "NEW JUNK CITY": "map_images/New_Junk_City.jpg",
        "NEW QUEEN STREET": "map_images/New_Queens_Street.jpg",
        "NUMBANI": "map_images/Numbani.jpg",
        "OASIS": "map_images/Oasis.jpg",
        "PARAÍSO": "map_images/Paraiso.png",
        "RIALTO": "map_images/Rialto.jpg",
        "ROUTE 66": "map_images/Route-66.jpg",
        "RUNASAPI": "map_images/Runasapi.jpg",
        "SAMOA": "map_images/Samoa.jpg",
        "SHAMBALI MONASTERY": "map_images/Shambali.jpg",
        "SURAVASA": "map_images/Suravasa.jpg",
        "WATCHPOINT: GIBRALTAR": "map_images/Watchpoint-gibraltar.jpg"
    }
    percentiles = df_maps["Votes_per_Appearance"].rank(pct=True)
    def get_tier(p):
        if p >= 0.84:
            return "S"
        elif p >= 0.69:
            return "A"
        elif p >= 0.5:
            return "B"
        elif p >= 0.31:
            return "C"
        elif p >= 0.16:
            return "D"
        else:
            return "F"
    df_maps["Tier"] = percentiles.apply(get_tier)
    # Define a fixed number of columns per row
    columns_per_row = 6
    image_width = 100
    st.subheader("Map Tier List (based on Votes per Appearance)")
    tiers = ["S", "A", "B", "C", "D", "F"]
    for tier in tiers:
        tier_maps = df_maps[df_maps["Tier"] == tier].sort_values("Votes_per_Appearance", ascending=False)
        rows = [tier_maps.iloc[i:i + columns_per_row] for i in range(0, len(tier_maps), columns_per_row)]
        for row_index, row_df in enumerate(rows):
            cols = st.columns(columns_per_row + 1)  # +1 for the tier label column
            if row_index == 0:
                with cols[0]:
                    st.markdown(f"### Tier {tier}")
            else:
                with cols[0]:
                    st.markdown(" ")  # empty to align with image rows
            for col, (_, row) in zip(cols[1:], row_df.iterrows()):
                with col:
                    st.image(
                        map_image_filenames[row["Map Name"]],
                        caption=row["Map Name"],
                        width=image_width
                    )


    # --- BAR CHARTS ---
    st.subheader("Bar Charts")
    fig_votes_per_appearance = px.bar(
        df_maps.sort_values("Votes_per_Appearance", ascending=False),
        x="Map Name",
        y="Votes_per_Appearance",
        color="Map Type",
        title="Votes per Appearance per Map",
        labels={"Votes_per_Appearance": "Votes per Appearance", "Map Name": "Map"},
        height=500,
        category_orders={"Map Name": df_maps.sort_values("Votes_per_Appearance", ascending=False)["Map Name"].tolist()}
    )
    st.plotly_chart(fig_votes_per_appearance, use_container_width=True)
    fig_percent_per_appearance = px.bar(
        df_maps.sort_values("Percent_per_Appearance", ascending=False),
        x="Map Name",
        y="Percent_per_Appearance",
        color="Map Type",
        title="Percent of Votes per Appearance per Map",
        labels={"Percent_per_Appearance": "% of Votes per Appearance", "Map Name": "Map"},
        height=500,
        category_orders={"Map Name": df_maps.sort_values("Percent_per_Appearance", ascending=False)["Map Name"].tolist()}
    )
    st.plotly_chart(fig_percent_per_appearance, use_container_width=True)
    fig_votes = px.bar(
        df_maps.sort_values("Total_Votes", ascending=False),
        x="Map Name",
        y="Total_Votes",
        color="Map Type",
        title="Total Votes per Map",
        labels={"Total_Votes": "Total Votes", "Map Name": "Map"},
        height=500,
        category_orders={"Map Name": df_maps.sort_values("Total_Votes", ascending=False)["Map Name"].tolist()}
    )
    st.plotly_chart(fig_votes, use_container_width=True)
    fig_percent = px.bar(
        df_maps.sort_values("Total_Percent_of_Votes", ascending=False),
        x="Map Name",
        y="Total_Percent_of_Votes",
        color="Map Type",
        title="Total Vote Percent per Map",
        labels={"Total_Percent_of_Votes": "Total % of Votes", "Map Name": "Map"},
        height=500,
        category_orders={"Map Name": df_maps.sort_values("Total_Percent_of_Votes", ascending=False)["Map Name"].tolist()}
    )
    st.plotly_chart(fig_percent, use_container_width=True)

    # --- VOTES BY CARD ---
    st.subheader("Votes by Card")
    df_votes_by_card = df_wl[['votes1', 'votes2', 'votes3']].sum().reset_index()
    df_votes_by_card.columns = ['Card', 'Votes']
    df_votes_by_card['Card'] = df_votes_by_card['Card'].replace({
        'votes1': 'Left',
        'votes2': 'Middle',
        'votes3': 'Right'
    })
    fig_votes_by_card = px.pie(
        df_votes_by_card,
        values='Votes',
        names='Card',
        title='Total Votes by Card',
        labels={'Votes': 'Total Votes', 'Card': 'Card'},
        height=500
    )
    st.plotly_chart(fig_votes_by_card, use_container_width=True)

    # --- MAP DATA ---
    st.subheader("Map Data")
    st.dataframe(df_maps, hide_index=True)

    # --- RAW DATA ---
    st.subheader("Raw Data")
    st.dataframe(df_wl)

    # --- METHODOLOGY ---
    st.subheader("Methodology")
    st.markdown("""
                This project uses machine vision to automatically look through Twitch VODs for map voting data. 
                
                Note that this data has been limited to a selected whitelist of streamers selected for their generally high rank,
                streams that mostly consist of competitive play (no stadium), and play in the english language, as those streams consistenly
                gave data without wasting processing time.
                
                The Tier List is split up based on an assumption of standard deviations. S Tier includes maps with total votes above the 84th Percentile, 
                making them a full standard deviation away. A tier is above half a standard deviation, above the 69th percentile, and so on.
                
                If you're a fan of this work, [follow me on twitter.](http://twitter.com/qghop_) Thanks!
                """)
