import streamlit as st
import pandas as pd
import plotly.express as px

import src.clean as clean

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
[Map Tier List](#map-tier-list-based-on-votes-per-appearance)

[Bar Charts, by Map](#bar-charts)

[Votes by Card](#votes-by-card)

[Box Plot, Participation per Vote](#box-plot)

[Appearances vs Total Votes](#appearances-vs-total-votes-per-map)

[Map Data](#map-data)

[Raw Data](#raw-data)

[Methodology](#methodology)
""")

left, center, right = st.columns([1, 5, 1])
with center:

    # --- TITLE ---
    st.title("Overwatch Map Voting Data")
    st.write("Data on Map Voting in Grandmaster, NA + EMEA Lobbies, extracted from public Twitch VODs.")
    st.write("Updated as of 2025-07-18.")

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
                    st.markdown(f"### {tier} Tier")
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
    map_type_colors = {
        "Control": "#1f77b4",
        "Escort": "#ff7f0e",
        "Flashpoint": "#2ca02c",
        "Hybrid": "#d62728",
        "Push": "#9467bd"
    }
    st.subheader("Bar Charts")
    fig_votes_per_appearance = px.bar(
        df_maps.sort_values("Votes_per_Appearance", ascending=False),
        x="Map Name",
        y="Votes_per_Appearance",
        color="Map Type",
        color_discrete_map=map_type_colors,
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
        color_discrete_map=map_type_colors,
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
        color_discrete_map=map_type_colors,
        title="Total Votes per Map",
        labels={"Total_Votes": "Total Votes", "Map Name": "Map"},
        height=500,
        category_orders={"Map Name": df_maps.sort_values("Total_Votes", ascending=False)["Map Name"].tolist()}
    )
    st.plotly_chart(fig_votes, use_container_width=True)
    
    # fig_percent = px.bar(
    #     df_maps.sort_values("Total_Percent_of_Votes", ascending=False),
    #     x="Map Name",
    #     y="Total_Percent_of_Votes",
    #     color="Map Type",
    #     color_discrete_map=map_type_colors,
    #     title="Total Vote Percent per Map",
    #     labels={"Total_Percent_of_Votes": "Total % of Votes", "Map Name": "Map"},
    #     height=500,
    #     category_orders={"Map Name": df_maps.sort_values("Total_Percent_of_Votes", ascending=False)["Map Name"].tolist()}
    # )
    # st.plotly_chart(fig_percent, use_container_width=True)

    fig_win_percentage = px.bar(
        df_maps.sort_values("Win_Percentage", ascending=False),
        x="Map Name",
        y="Win_Percentage",
        color="Map Type",
        color_discrete_map=map_type_colors,
        title="Win Percentage (Gets the Majority of Votes) per Map",
        labels={"Win_Percentage": "Win Percentage", "Map Name": "Map"},
        height=500,
        category_orders={"Map Name": df_maps.sort_values("Win_Percentage", ascending=False)["Map Name"].tolist()}
    )
    st.plotly_chart(fig_win_percentage, use_container_width=True)
    
    # Scatterplot of winrate vs votes per appearance
    # Commented out, not very interesting
    # fig_winrate_vs_votes = px.scatter(
    #     df_maps,
    #     x="Votes_per_Appearance",
    #     y="Win_Percentage",
    #     color="Map Type",
    #     color_discrete_map=map_type_colors,
    #     title="Win Percentage vs Votes per Appearance per Map",
    #     labels={"Votes_per_Appearance": "Votes per Appearance", "Win_Percentage": "Win Percentage"},
    #     hover_data=["Map Name"],
    #     height=500,
    #     category_orders={"Map Name": df_maps.sort_values("Votes_per_Appearance", ascending=False)["Map Name"].tolist()}
    # )
    # fig_winrate_vs_votes.update_traces(marker=dict(size=10))
    # st.plotly_chart(fig_winrate_vs_votes, use_container_width=True)
    

    # --- VOTES BY CARD ---
    card_color_map = {
        'Left': "#d3301a",
        'Middle': "#419b1e",
        'Right': "#2b35b6"
    }

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
        color='Card',
        color_discrete_map=card_color_map,
        height=500
    )
    st.plotly_chart(fig_votes_by_card, use_container_width=True)

    st.subheader("Vote Distribution per Card")
    df_votes_long = df_wl[['votes1', 'votes2', 'votes3']].rename(columns={
        'votes1': 'Left',
        'votes2': 'Middle',
        'votes3': 'Right'
    }).melt(var_name='Card', value_name='Votes')
    fig_votes_hist = px.histogram(
        df_votes_long,
        x='Votes',
        color='Card',
        nbins=11,
        barmode='group',
        category_orders={'Votes': list(range(0, 11))},
        labels={'Votes': 'Votes per Event', 'Card': 'Card'},
        title='Distribution of Votes per Card',
        color_discrete_map=card_color_map,
    )
    fig_votes_hist.update_layout(
        xaxis=dict(tickmode='linear', dtick=1),
        yaxis_title='Frequency',
        height=500
    )
    st.plotly_chart(fig_votes_hist, use_container_width=True)


    # --- BOX PLOT ---
    # Box plot of total participation
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Box Plot")
        st.write("Total Participation per Map Vote Event")
        st.write(f"Total Number of Map Vote Events Logged: {len(df_wl)}")
        st.write("""
                Note that 0 and 1 total vote scenarios have been removed from the dataset, 
                as they are rare and more often than not come from errors in the data collection process.
                
                
                Also note that vote events where all 10 players voted for the same map are counted as just 9 votes due to 
                the method of collecting (very few, if any frames on screen show 0, 0, and 10 votes).
                """)
    with c2:
        fig_box_plot = px.box(
            df_wl,
            y='total_votes',
            labels={'total_votes': 'Total Votes'},
            height=450,
            boxmode='overlay',
            points='all',
        )
        fig_box_plot.update_traces(marker=dict(size=5, opacity=0.6, color='blue'))
        fig_box_plot.update_layout(yaxis_title='Total Votes')
        st.plotly_chart(fig_box_plot, use_container_width=True)
    
    # --- SCATTER PLOT, APPEARANCES VS VOTES --- 
    st.subheader("Appearances vs Total Votes per Map")
    fig_appearances_vs_votes = px.scatter(
        df_maps,
        x='Appearances',
        y='Total_Votes',
        color='Map Type',
        color_discrete_map=map_type_colors,
        title='Appearances vs Total Votes per Map',
        labels={'Appearances': 'Appearances', 'Total_Votes': 'Total Votes'},
        hover_data=['Map Name'],
        height=500,
        category_orders={'Map Name': df_maps.sort_values('Total_Votes', ascending=False)['Map Name'].tolist()}
    )
    fig_appearances_vs_votes.update_traces(marker=dict(size=10))
    st.plotly_chart(fig_appearances_vs_votes, use_container_width=True)

    # --- MAP DATA ---
    st.subheader("Map Data")
    st.dataframe(df_maps, hide_index=True)

    # --- RAW DATA ---
    st.subheader("Raw Data")
    st.dataframe(df_wl)

    # --- METHODOLOGY ---
    st.subheader("Methodology")
    st.markdown("""
                This project uses machine vision to automatically look through Twitch VODs for map voting data, making use of OpenCV, EasyOCR, FFmpeg, and more.
                
                Note that this data has been limited to a selected whitelist of streamers selected for their generally high rank,
                streams that mostly consist of competitive play (no stadium), and play in the english language, as those streams consistenly
                gave data without wasting processing time. I've done work to make the existing data as accurate as possible, but I wouldn't be suprised
                if I messed something up, so take this all with a grain of salt. For example, I think there's reasonable evidence that map appearances
                are imbalanced in the actual game (higher chance of new maps, lower chance of getting a map commonly played) but a lot of that could
                also be attributed to bad code and OCR bias, so the x/per appearances counts are more valuable. 
                
                The Tier List is split up based on an assumption of standard deviations. S Tier includes maps with total votes above the 84th Percentile, 
                making them a full standard deviation away. A tier is above half a standard deviation, above the 69th percentile, and so on.
                
                Win Percentage is calculated by simple majority vote, rather than the actual selection by the game. Ties do not count as wins for any map.
                
                If you're a fan of this work, [follow me on twitter.](http://twitter.com/qghop_) Thanks! I'll try to keep it updated throughout the season.
                """)


# Reminder, run with streamlit run streamlit_app.py