def get_named_parameter(event, name):
    return event[name]


def handle_create_booking(event):
    bookingDate = get_named_parameter(event, "date")
    bookingHour = get_named_parameter(event, "hour")
    restaurantName = get_named_parameter(event, "restaurant_name")
    guestName = get_named_parameter(event, "guest_name")
    numGuests = int(get_named_parameter(event, "num_guests"))
    return f"Booking id 12345, for {numGuests} guests at {restaurantName} on {bookingDate} at {bookingHour} for {guestName} created."


def lambda_handler(event, context):
    print(f"event: {event}")
    print(f"context: {context}")
    print(f"context.client_context: {context.client_context}")

    # Bedrock Agent Core에서 전달된 tool 이름 추출
    extended_tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    # "___" 구분자로 분리하여 실제 tool 이름만 가져옴 (예: "prefix___create_booking" -> "create_booking")
    tool_name = extended_tool_name.split("___")[1]

    print(f"tool_name: {tool_name}")

    if tool_name == "create_booking":
        result = handle_create_booking(event)
    else:
        result = f"Unrecognized tool_name: {tool_name}"

    print(f"result: {result}")
    return result
