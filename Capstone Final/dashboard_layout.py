"""Dash layout definition kept separate from callback/controller logic.

This module defines what the user sees. It intentionally contains no database
operations or callback behavior, keeping presentation separate from application
logic.
"""

import base64
from pathlib import Path
from typing import Iterable

from dash import dcc, html, dash_table

# Define table columns once so the DataTable configuration is easy to maintain.
# Calculated ranking fields are included alongside the original animal data.
TABLE_COLUMNS = [
    {"name": "Name", "id": "name"},
    {"name": "Breed", "id": "breed"},
    {"name": "Sex", "id": "sex_upon_outcome"},
    {"name": "Age", "id": "age_upon_outcome"},
    {"name": "Outcome", "id": "outcome_type"},
    {"name": "Latitude", "id": "location_lat"},
    {"name": "Longitude", "id": "location_long"},
    {"name": "Suitability Score", "id": "suitability_score", "type": "numeric"},
    {"name": "Match", "id": "match_level"},
    {"name": "Matched Criteria", "id": "match_reasons"},
]


def _logo_component() -> html.Div:
    """Return the shelter logo when available, otherwise return a text title."""
    # Check both the module directory and current working directory so the image
    # can still be found when the project is launched in different ways.
    possible = [
        Path(__file__).with_name("GraziosoSalvareLogo.png"),
        Path.cwd() / "GraziosoSalvareLogo.png",
    ]
    logo_path = next((path for path in possible if path.exists()), None)

    # A missing image should not stop the dashboard from loading.
    if logo_path is None:
        return html.Div("Grazioso Salvare Animal Shelter Dashboard")

    # Embed the image as a base64 data URI so Dash can display the local file.
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return html.Div(
        html.Img(src=f"data:image/png;base64,{encoded}", style={"height": "64px"}),
        style={"textAlign": "center"},
    )


def build_layout(profile_names: Iterable[str]) -> html.Div:
    """Build and return the complete visual layout for the dashboard."""
    # Add a neutral "All Animals" option before the configured rescue profiles.
    rescue_options = [{"label": "All Animals", "value": "ALL"}]
    rescue_options.extend({"label": name, "value": name} for name in profile_names)

    # The layout is divided into rescue ranking, record management, the data
    # table, and visualization sections. Behavior is attached elsewhere.
    return html.Div(
        [
            html.Center(html.H1("Greg Gordon's CS-340 Animal Shelter Dashboard")),
            _logo_component(),
            html.Hr(),

            # Rescue-ranking controls.
            html.H3("Rescue Candidate Ranking"),
            html.P(
                "Choose a rescue type to score and rank dogs using the configurable "
                "criteria in rescue_profiles.json."
            ),
            dcc.RadioItems(
                id="rescue-profile",
                options=rescue_options,
                value="ALL",
                inline=True,
            ),
            html.Hr(),

            # CRUD form. Blank values are intentionally ignored during updates so
            # the user can change only the fields they want to modify.
            html.H3("Animal Record Management"),
            html.P(
                "Select a table row to edit or delete it. Blank fields are ignored "
                "during updates."
            ),
            html.Div(
                [
                    dcc.Input(id="animal-name", type="text", placeholder="Name"),
                    dcc.Input(
                        id="animal-type",
                        type="text",
                        placeholder="Animal type",
                        value="Dog",
                    ),
                    dcc.Input(id="animal-breed", type="text", placeholder="Breed"),
                    dcc.Input(
                        id="animal-sex", type="text", placeholder="Sex upon outcome"
                    ),
                    dcc.Input(
                        id="animal-age-weeks",
                        type="number",
                        placeholder="Age in weeks",
                    ),
                    dcc.Input(
                        id="animal-outcome", type="text", placeholder="Outcome type"
                    ),
                    dcc.Input(id="animal-lat", type="number", placeholder="Latitude"),
                    dcc.Input(id="animal-lon", type="number", placeholder="Longitude"),
                ],
                style={"display": "flex", "gap": "6px", "flexWrap": "wrap"},
            ),
            html.Br(),

            # CRUD buttons. Delete requires an extra confirmation checkbox to
            # reduce accidental destructive actions.
            html.Div(
                [
                    html.Button("Create", id="create-record", n_clicks=0),
                    html.Button("Update Selected", id="update-record", n_clicks=0),
                    html.Button("Delete Selected", id="delete-record", n_clicks=0),
                    dcc.Checklist(
                        id="confirm-delete",
                        options=[{"label": "Confirm delete", "value": "confirm"}],
                        value=[],
                        inline=True,
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "8px",
                    "alignItems": "center",
                    "flexWrap": "wrap",
                },
            ),

            # This region displays create/update/delete success or error messages.
            html.Div(id="crud-status", style={"marginTop": "8px"}),
            html.Hr(),

            # Interactive table used both for viewing records and selecting one
            # record for update/delete operations.
            dash_table.DataTable(
                id="datatable-id",
                columns=TABLE_COLUMNS,
                data=[],
                page_size=10,
                sort_action="native",
                filter_action="native",
                column_selectable="single",
                row_selectable="single",
                selected_rows=[],
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "minWidth": "90px",
                    "maxWidth": "260px",
                },
            ),
            html.Br(),
            html.Hr(),

            # Graph and map share the bottom row and wrap on smaller displays.
            html.Div(
                className="row",
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
                children=[
                    html.Div(id="graph-id", style={"flex": "1", "minWidth": "420px"}),
                    html.Div(id="map-id", style={"flex": "1", "minWidth": "420px"}),
                ],
            ),
        ]
    )
