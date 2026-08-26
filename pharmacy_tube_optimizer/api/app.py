"""Small dependency-free WSGI REST API for the tubing board."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

from pharmacy_tube_optimizer.config import TUBING_BIN_LOCATIONS
from pharmacy_tube_optimizer.data.mock_data_generator import (
    generate_random_medication_orders,
    generate_random_mock_dataset,
    place_orders_in_bins,
)
from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.services.bin_state_service import BinStateService
from pharmacy_tube_optimizer.services.medication_service import MedicationService
from pharmacy_tube_optimizer.services.override_service import OverrideService
from pharmacy_tube_optimizer.services.tubing_engine import TubingEngine
from pharmacy_tube_optimizer.utils.logger import Logger


class MediTubeApi:
    """WSGI application whose routes delegate all decisions to the engine."""

    def __init__(
        self,
        bins: list[Bin],
        orders: list[MedicationOrder],
        *,
        engine: TubingEngine | None = None,
        state_service: BinStateService | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.bins = bins
        self.engine = engine or TubingEngine()
        self.state_service = state_service or BinStateService()
        self.clock = clock or datetime.now
        self.logger = Logger(clock=self.clock)
        self.medication_service = MedicationService(orders, self.logger)
        self.override_service = OverrideService(self.logger)

    def __call__(self, environ: dict, start_response: Callable):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/").rstrip("/") or "/"
        if method == "GET" and path == "/bins":
            return self._respond(start_response, "200 OK", self._board_state())
        if method == "POST" and path == "/simulation/refresh":
            return self._refresh_simulation(start_response)

        path_parts = path.strip("/").split("/")
        if len(path_parts) == 2 and path_parts[0] == "bins" and method == "GET":
            return self._respond_for_bin(start_response, path_parts[1])
        if len(path_parts) == 3 and path_parts[0] == "bins" and path_parts[2] == "tube" and method == "POST":
            return self._tube_bin(start_response, path_parts[1])
        if len(path_parts) == 3 and path_parts[0] == "bins" and path_parts[2] == "force-tube" and method == "POST":
            return self._force_tube_bin(start_response, path_parts[1])

        return self._respond(start_response, "404 Not Found", {"error": "Route not found"})

    def _board_state(self) -> dict:
        # The engine owns transfer detection and reconciliation; this API only
        # requests the prepared state and serializes it.
        evaluation = self.engine.prepare_tubing(self.bins, self.clock())
        return self._with_tubed_medications(self.state_service.get_board_state(self.bins, evaluation))

    def _respond_for_bin(self, start_response: Callable, raw_bin_id: str):
        state = self._board_state()
        normalized = self._normalize_bin_id(raw_bin_id)
        bin_state = self.state_service.get_bin_state(normalized, self.bins, self.engine.evaluate(self.bins, self.clock()))
        if bin_state is None:
            return self._respond(start_response, "404 Not Found", {"error": "Bin not found"})
        return self._respond(
            start_response,
            "200 OK",
            {"bin": bin_state, "detected_transfers": state["detected_transfers"]},
        )

    def _tube_bin(self, start_response: Callable, raw_bin_id: str):
        bin_id = self._normalize_bin_id(raw_bin_id)
        if bin_id not in TUBING_BIN_LOCATIONS:
            return self._respond(start_response, "404 Not Found", {"error": "Bin not found"})

        # A fresh prepare pass detects/moves transfers and re-evaluates before
        # the engine performs the requested, explicit tubing action.
        evaluation = self.engine.prepare_tubing(self.bins, self.clock())
        tubed_orders = self.engine.execute_tubing(
            evaluation, self.bins, self.medication_service, selected_bins=[bin_id]
        )
        updated_evaluation = self.engine.prepare_tubing(self.bins, self.clock())
        response = self._with_tubed_medications(self.state_service.get_board_state(self.bins, updated_evaluation))
        # Report transfers detected during the final pre-tube check even
        # though the follow-up state evaluation sees their new bin placement.
        response["detected_transfers"] = list(evaluation.detected_transfers)
        response["tubed_order_numbers"] = [order.order_number for order in tubed_orders]
        return self._respond(start_response, "200 OK", response)

    def _force_tube_bin(self, start_response: Callable, raw_bin_id: str):
        """Perform a technician-approved tubing override for one bin."""
        bin_id = self._normalize_bin_id(raw_bin_id)
        if bin_id not in TUBING_BIN_LOCATIONS:
            return self._respond(start_response, "404 Not Found", {"error": "Bin not found"})

        # Transfers still receive their final backend check before the manual
        # override applies to the bin's actual current contents.
        evaluation = self.engine.prepare_tubing(self.bins, self.clock())
        bin_obj = next((candidate for candidate in self.bins if candidate.bin_number == bin_id), Bin(bin_id))
        override = self.override_service.override_tubing_decision(bin_obj)
        tubed_orders = self.engine.execute_manual_tubing(bin_id, self.bins, self.medication_service)
        updated_evaluation = self.engine.prepare_tubing(self.bins, self.clock())
        response = self._with_tubed_medications(self.state_service.get_board_state(self.bins, updated_evaluation))
        response["detected_transfers"] = list(evaluation.detected_transfers)
        response["tubed_order_numbers"] = [order.order_number for order in tubed_orders]
        response["manual_override"] = override
        return self._respond(start_response, "200 OK", response)

    def _refresh_simulation(self, start_response: Callable):
        """Append a generated medication batch and return its evaluated board."""
        new_orders = generate_random_medication_orders(
            10,
            reference_time=self.clock(),
            reserved_order_ids={order.order_id for order in self.medication_service.orders},
        )
        place_orders_in_bins(new_orders, self.bins)
        self.medication_service.orders.extend(new_orders)

        # This performs the normal engine-owned transfer reconciliation and
        # final evaluation, but does not execute tubing.
        response = self._board_state()
        response["generated_order_numbers"] = [order.order_number for order in new_orders]
        return self._respond(start_response, "200 OK", response)

    def _with_tubed_medications(self, board_state: dict) -> dict:
        """Attach backend-confirmed tubing history to a board response."""
        board_state["tubed_medications"] = [
            order.get_order_information()
            for order in self.medication_service.get_tubed_medications()
        ]
        return board_state

    @staticmethod
    def _normalize_bin_id(raw_bin_id: str) -> int | str:
        value = raw_bin_id.strip().upper()
        if value.startswith("BIN_"):
            value = value[4:]
        return int(value) if value.isdigit() else value

    @staticmethod
    def _respond(start_response: Callable, status: str, payload: dict):
        encoded = json.dumps(payload).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(encoded)))])
        return [encoded]


def create_app(
    bins: list[Bin] | None = None,
    orders: list[MedicationOrder] | None = None,
    *,
    clock: Callable[[], datetime] | None = None,
) -> MediTubeApi:
    """Create the REST application, generating a live board when none is supplied.

    The generated bins and orders are created once per API-process start and
    retained in memory thereafter.  GET requests therefore reflect the real
    current tubing state instead of replacing it with new mock data.
    """
    if bins is None or orders is None:
        _, generated_bins, generated_orders = generate_random_mock_dataset(reference_time=(clock() if clock else None))
        bins = bins or generated_bins
        orders = orders or generated_orders
    return MediTubeApi(bins, orders, clock=clock)
