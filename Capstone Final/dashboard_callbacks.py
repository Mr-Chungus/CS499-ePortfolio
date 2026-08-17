"""Dashboard controller/callback logic.

This module contains the behavior behind the interface defined in
``dashboard_layout.py``. Keeping callback logic separate from layout code makes
it easier to locate, test, and modify application behavior.
"""

import logging
from typing import Any, Dict, List, Mapping

import dash
import dash_leaflet as dl
from dash import Input, Output, State, dcc, html
import pandas as pd
import plotly.express as px

from rescue_ranking import rank_animals

LOGGER = logging.getLogger(__name__)


def _dashboard_records(
    db: Any,
    profile_name: str,
    profiles: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Read MongoDB records and optionally add rescue suitability ranking."""
    # With no rescue profile selected, return all animals. When a rescue profile
    # is selected, only dogs need to be evaluated by the ranking algorithm.
    query: Dict[str, Any] = {}
    if profile_name and profile_name != "ALL":
        # Breeds that are not preferred are still included; they simply receive
        # zero breed points instead of being removed by a hard database filter.
        query = {"animal_type": {"$in": ["Dog", "dog"]}}

    records = db.read(query) or []
    safe_records: List[Dict[str, Any]] = []

    # MongoDB's ObjectId is not JSON serializable, so convert _id to a string
    # called record_id before sending records to Dash components.
    for record in records:
        item = dict(record)
        object_id = item.pop("_id", None)
        item["record_id"] = str(object_id) if object_id is not None else None
        safe_records.append(item)

    # Add calculated score, match level, and match reasons when a rescue profile
    # is active. rank_animals also sorts strongest candidates first.
    if profile_name and profile_name != "ALL":
        return rank_animals(safe_records, profile_name, profiles)

    # When viewing all animals, keep the same table columns but leave calculated
    # ranking values blank because no rescue profile is being evaluated.
    for item in safe_records:
        item["suitability_score"] = None
        item["match_level"] = ""
        item["match_reasons"] = ""

    return safe_records


def register_callbacks(
    app: Any,
    db: Any,
    profiles: Mapping[str, Mapping[str, Any]],
) -> None:
    """Attach all controller callbacks to a Dash or JupyterDash application."""

    @app.callback(
        [Output("datatable-id", "data"), Output("crud-status", "children")],
        [
            Input("rescue-profile", "value"),
            Input("create-record", "n_clicks"),
            Input("update-record", "n_clicks"),
            Input("delete-record", "n_clicks"),
        ],
        [
            State("datatable-id", "derived_virtual_data"),
            State("datatable-id", "derived_virtual_selected_rows"),
            State("animal-name", "value"),
            State("animal-type", "value"),
            State("animal-breed", "value"),
            State("animal-sex", "value"),
            State("animal-age-weeks", "value"),
            State("animal-outcome", "value"),
            State("animal-lat", "value"),
            State("animal-lon", "value"),
            State("confirm-delete", "value"),
        ],
    )
    def update_dashboard(
        profile_name,
        create_clicks,
        update_clicks,
        delete_clicks,
        view_data,
        selected_rows,
        name,
        animal_type,
        breed,
        sex,
        age_weeks,
        outcome,
        lat,
        lon,
        confirm_delete,
    ):
        """Handle rescue selection and create/update/delete button actions."""
        # The click counts only cause Dash to invoke this callback. The identity
        # of the triggering component is obtained from callback_context below.
        del create_clicks, update_clicks, delete_clicks

        # Determine whether this callback was triggered by the rescue selector or
        # one of the CRUD buttons so only the requested operation is performed.
        trigger = (
            dash.callback_context.triggered[0]["prop_id"].split(".")[0]
            if dash.callback_context.triggered
            else "rescue-profile"
        )
        status = ""

        # Build one dictionary from the form inputs. Blank fields are removed so
        # updates change only values the user actually entered.
        form_data = {
            "name": name,
            "animal_type": animal_type,
            "breed": breed,
            "sex_upon_outcome": sex,
            "age_upon_outcome_in_weeks": age_weeks,
            "outcome_type": outcome,
            "location_lat": lat,
            "location_long": lon,
        }
        update_data = {
            key: value for key, value in form_data.items() if value not in (None, "")
        }

        # CREATE: validation and normalization are handled by the database layer.
        if trigger == "create-record":
            result = db.create(update_data)
            status = (
                "Record created."
                if result.get("success")
                else f"Create failed: {result.get('error')}"
            )

        # UPDATE/DELETE both require a valid selected table row and record_id.
        elif trigger in ("update-record", "delete-record"):
            if not view_data or not selected_rows:
                status = "Select a record in the table first."
            else:
                row_index = selected_rows[0]

                # Defensive check in case filtering/sorting changed the visible
                # table after a row had previously been selected.
                if row_index >= len(view_data):
                    status = "The selected row is no longer available."
                else:
                    record_id = view_data[row_index].get("record_id")

                    if not record_id:
                        status = "Selected record does not contain a database ID."

                    # UPDATE: require at least one nonblank field to change.
                    elif trigger == "update-record":
                        if not update_data:
                            status = "Enter at least one value to update."
                        else:
                            result = db.update({"_id": record_id}, update_data)
                            status = (
                                f"Updated {result.get('modified_count', 0)} record(s)."
                                if result.get("success")
                                else f"Update failed: {result.get('error')}"
                            )

                    # DELETE: require an explicit confirmation checkbox before the
                    # selected record is removed from MongoDB.
                    else:
                        if "confirm" not in (confirm_delete or []):
                            status = "Check Confirm delete before deleting a record."
                        else:
                            result = db.delete({"_id": record_id})
                            status = (
                                f"Deleted {result.get('deleted_count', 0)} record(s)."
                                if result.get("success")
                                else f"Delete failed: {result.get('error')}"
                            )

        # Refresh the table after any operation so the UI reflects the current
        # database state and current rescue-ranking selection.
        try:
            return _dashboard_records(db, profile_name, profiles), status
        except ValueError as exc:
            # Ranking configuration errors should not crash the whole dashboard.
            LOGGER.exception("Unable to rank rescue candidates")
            return [], f"Ranking failed: {exc}"

    @app.callback(
        [
            Output("animal-name", "value"),
            Output("animal-type", "value"),
            Output("animal-breed", "value"),
            Output("animal-sex", "value"),
            Output("animal-age-weeks", "value"),
            Output("animal-outcome", "value"),
            Output("animal-lat", "value"),
            Output("animal-lon", "value"),
        ],
        [
            Input("datatable-id", "derived_virtual_data"),
            Input("datatable-id", "derived_virtual_selected_rows"),
        ],
        prevent_initial_call=True,
    )
    def populate_form(view_data, selected_rows):
        """Copy the selected table row into the edit form."""
        # Keep existing form values when selection data is missing or invalid.
        if not view_data or not selected_rows or selected_rows[0] >= len(view_data):
            return (dash.no_update,) * 8

        # The selected row becomes the source for the editable form fields.
        row = view_data[selected_rows[0]]
        return (
            row.get("name"),
            row.get("animal_type"),
            row.get("breed"),
            row.get("sex_upon_outcome"),
            row.get("age_upon_outcome_in_weeks"),
            row.get("outcome_type"),
            row.get("location_lat"),
            row.get("location_long"),
        )

    @app.callback(
        Output("graph-id", "children"), Input("datatable-id", "derived_virtual_data")
    )
    def update_graph(view_data):
        """Build a bar chart showing the most common breeds in the current view."""
        # Convert the currently visible/filtered Dash records into a DataFrame.
        dff = pd.DataFrame(view_data or [])
        if dff.empty or "breed" not in dff.columns:
            return html.Div("No data to display.")

        # Count breed occurrences and reshape the result for Plotly Express.
        counts = (
            dff["breed"]
            .value_counts(dropna=True)
            .rename_axis("breed")
            .reset_index(name="count")
        )

        # Limit the graph to the top 12 breeds. Any remaining breeds are combined
        # into "Other" so the chart remains readable with larger result sets.
        top_n = 12
        if len(counts) > top_n:
            other_sum = int(counts.loc[top_n:, "count"].sum())
            counts = counts.head(top_n).copy()
            counts.loc[len(counts)] = ["Other", other_sum]

        # Horizontal bars keep longer breed names readable.
        fig = px.bar(
            counts.sort_values("count"),
            x="count",
            y="breed",
            orientation="h",
            title="Top Breeds in Current View",
        )

        # Increase the figure height based on the number of displayed categories.
        fig.update_layout(
            margin=dict(l=10, r=10, t=40, b=40),
            height=400 + 20 * len(counts),
            xaxis_title="Count",
            yaxis_title="",
        )
        return dcc.Graph(figure=fig)

    @app.callback(
        Output("datatable-id", "style_data_conditional"),
        Input("datatable-id", "selected_columns"),
    )
    def update_styles(selected_columns):
        """Visually highlight any column selected by the user."""
        # Dash expects a list of conditional style dictionaries, one per selected
        # column. An empty selection naturally returns an empty list.
        return [
            {"if": {"column_id": col}, "background_color": "#D2F3FF"}
            for col in (selected_columns or [])
        ]

    @app.callback(
        Output("map-id", "children"),
        [
            Input("datatable-id", "derived_virtual_data"),
            Input("datatable-id", "derived_virtual_selected_rows"),
        ],
    )
    def update_map(view_data, selected_rows):
        """Display the selected animal on a map when valid coordinates exist."""
        if not view_data:
            return html.Div("No rows in view.")

        # Work from the same visible table data the user is currently viewing.
        dff = pd.DataFrame(view_data)

        # Default to the first row when no explicit row has been selected, then
        # clamp the index so sorting/filtering cannot produce an invalid lookup.
        row_idx = (selected_rows or [0])[0]
        row_idx = max(0, min(row_idx, len(dff) - 1))

        # Pull the values needed for the map marker and popup, using safe defaults
        # when optional columns are missing.
        lat = dff.at[row_idx, "location_lat"] if "location_lat" in dff.columns else None
        lon = dff.at[row_idx, "location_long"] if "location_long" in dff.columns else None
        breed = dff.at[row_idx, "breed"] if "breed" in dff.columns else "Unknown"
        name = dff.at[row_idx, "name"] if "name" in dff.columns else "Unknown"

        # Use a default central location when the animal lacks usable coordinates.
        center_lat, center_lon = 30.75, -97.48
        valid_location = False

        try:
            lat_value = float(lat)
            lon_value = float(lon)
            valid_location = -90 <= lat_value <= 90 and -180 <= lon_value <= 180
        except (TypeError, ValueError):
            lat_value, lon_value = center_lat, center_lon

        # Add a marker only when both coordinates are valid. This prevents invalid
        # data from causing map-rendering errors.
        marker_children = []
        if valid_location:
            center_lat, center_lon = lat_value, lon_value
            marker_children = [
                dl.Marker(
                    position=[lat_value, lon_value],
                    children=[
                        dl.Tooltip(str(breed)),
                        dl.Popup([html.H4("Animal Name"), html.P(str(name))]),
                    ],
                )
            ]

        # The base tile layer is always rendered; a marker is appended only when
        # valid animal coordinates are available.
        return dl.Map(
            style={"width": "100%", "height": "500px"},
            center=[center_lat, center_lon],
            zoom=10,
            children=[dl.TileLayer(id="base-layer-id")] + marker_children,
        )
