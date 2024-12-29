from enum import Enum


class DeribitWsRequestError(Exception):
    """
    Exception thrown when Deribit request via websocked fails.

    Parameters
    ----------
    response: dict
        Error response received from Deribit.
    """

    def __init__(self, response: str) -> None:
        self.message = response["error"]["message"]
        self.status_code = response["error"]["code"]
        self.code = self.status_code


class ErrorStatus(Enum):
    RETRY = {
        10028: "too_many_requests",
        10040: "retry",
        10041: "settlement_in_progress",
        10047: "matching_engine_queue_full",
        10066: "too_many_concurrent_requests",
        13780: "move_positions_over_limit",
    }
    FATAL = {
        -32600: "request entity too large",
    }
    BLOCK = {
        11098: "account_locked",
        12003: "login_over_limit",
        12004: "registration_over_limit",
        12005: "country_is_banned",
        12998: "security_key_authorization_over_limit",
        13034: "no_more_security_keys_allowed",
    }
    IGNORE = {
        10002: "qty_too_low",
        10003: "order_overlap",
        10004: "order_not_found",
        10005: "price_too_low <Limit>",
        10006: "price_too_low4idx <Limit>",
        10007: "price_too_high <Limit>",
        10009: "not_enough_funds",
        10010: "already_closed",
        10011: "price_not_allowed",
        10012: "book_closed",
        10013: "pme_max_total_open_orders <Limit>",
        10014: "pme_max_future_open_orders <Limit>",
        10015: "pme_max_option_open_orders <Limit>",
        10016: "pme_max_future_open_orders_size <Limit>",
        10017: "pme_max_option_open_orders_size <Limit>",
        10018: "non_pme_max_future_position_size <Limit>",
        10019: "locked_by_admin",
        10020: "invalid_or_unsupported_instrument",
        10021: "invalid_amount",
        10022: "invalid_quantity",
        10023: "invalid_price",
        10024: "invalid_max_show",
        10025: "invalid_order_id",
        10026: "price_precision_exceeded",
        10027: "non_integer_contract_amount",
        10029: "not_owner_of_order",
        10030: "must_be_websocket_request",
        10031: "invalid_args_for_instrument",
        10032: "whole_cost_too_low",
        10033: "not_implemented",
        10034: "trigger_price_too_high",
        10035: "trigger_price_too_low",
        10036: "invalid_max_show_amount",
        10037: "non_pme_total_short_options_positions_size <Limit>",
        10038: "pme_max_risk_reducing_orders <Limit>",
        10043: "price_wrong_tick",
        10044: "trigger_price_wrong_tick",
        10045: "can_not_cancel_liquidation_order",
        10046: "can_not_edit_liquidation_order",
        10072: "disabled_while_position_lock",
        11008: "already_filled",
        11013: "max_spot_open_orders",
        11021: "post_only_price_modification_not_possible",
        11022: "max_spot_order_quantity",
        11029: "invalid_arguments",
        11030: "other_reject <Reason>",
        11031: "other_error <Error>",
        11035: "no_more_triggers <Limit>",
        11036: "invalid_trigger_price",
        11037: "outdated_instrument_for_IV_order",
        11038: "no_adv_for_futures",
        11039: "no_adv_postonly",
        11041: "not_adv_order",
        11042: "permission_denied",
        11043: "bad_argument",
        11044: "not_open_order",
        11045: "invalid_event",
        11046: "outdated_instrument",
        11047: "unsupported_arg_combination",
        11048: "wrong_max_show_for_option",
        11049: "bad_arguments",
        11050: "bad_request",
        11051: "system_maintenance",
        11052: "subscribe_error_unsubscribed",
        11053: "transfer_not_found",
        11054: "post_only_reject",
        11055: "post_only_not_allowed",
        11090: "invalid_addr",
        11091: "invalid_transfer_address",
        11092: "address_already_exist",
        11093: "max_addr_count_exceeded",
        11094: "internal_server_error",
        11095: "disabled_deposit_address_creation",
        11096: "address_belongs_to_user",
        11097: "no_deposit_address",
        12001: "too_many_subaccounts",
        12002: "wrong_subaccount_name",
        12100: "transfer_not_allowed",
        13008: "request_failed",
        13010: "value_required",
        13011: "value_too_short",
        13012: "unavailable_in_subaccount",
        13013: "invalid_phone_number",
        13014: "cannot_send_sms",
        13015: "invalid_sms_code",
        13016: "invalid_input",
        13018: "invalid_content_type",
        13019: "orderbook_closed",
        13020: "not_found",
        13025: "method_switched_off_by_admin",
        13028: "temporarily_unavailable",
        13031: "verification_required",
        13032: "non_unique_order_label",
        13035: "active_combo_limit_reached",
        13036: "unavailable_for_combo_books",
        13037: "incomplete_KYC_data",
        13040: "mmp_required",
        13042: "cod_not_enabled",
        13043: "quotes_frozen",
        13403: "scope_exceeded",
        13503: "unavailable",
        13666: "request_cancelled_by_user",
        13777: "replaced",
        13778: "raw_subscriptions_not_available_for_unauthorized",
        13781: "coupon_already_used",
        13791: "KYC_transfer_already_initiated",
        13792: "incomplete_KYC_data",
        13793: "KYC_data_inaccessible",
        13888: "timed_out",
        13901: "no_more_oto_orders",
        13902: "mass_quotes_disabled",
        13903: "too_many_quotes",
        -32602: "Invalid params",
        -32700: "Parse error",
    }
    CANCEL = {
        # 400: "Bad Request",
        401: "Unauthorized",
        404: "Not Found",
        10000: "authorization_required",
        10001: "error",
        10048: "not_on_this_server",
        10049: "cancel_on_disconnect_failed",
        11056: "unauthenticated_public_requests_temporarily_disabled",
        13004: "invalid_credentials",
        13005: "pwd_match_error",
        13006: "security_error",
        13007: "user_not_found",
        13009: "unauthorized",
        13021: "forbidden",
        -32601: "Method not found",
        -32000: "Missing params",
    }

    def error_status(error):
        error_number = error["error"]["code"]
        for status in ErrorStatus:
            if error_number in status.value:
                return status.name
