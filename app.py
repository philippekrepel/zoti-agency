import json
import os
import time
from flask import Flask, request, jsonify
import openai
from openai import OpenAI
import requests
import functions

from packaging import version

required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
OPENAI_API_KEY = os.environ.get("OPENAI_KEY")
if current_version < required_version:
  raise ValueError(
      f"Error: OpenAI version {openai.__version__} is less than the required version 1.1.1"
  )
else:
  print("OpenAI version is compatible.")

app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# Load assistant ID from file or create new one
assistant_id = "asst_oxk06TWR6Q3arNofK68dKjm1"
print("Assistant created with ID:", assistant_id)

# Create thread
@app.route('/start', methods=['GET'])
def start_conversation():
  thread = client.beta.threads.create()
  print("New conversation started with thread ID:", thread.id)
  return jsonify({"thread_id": thread.id})


# Start run
@app.route('/chat', methods=['POST'])
def chat():
  data = request.json
  thread_id = data.get('thread_id')
  user_input = data.get('message', '')
  if not thread_id:
    print("Error: Missing thread_id in /chat")
    return jsonify({"error": "Missing thread_id"}), 400
  print("Received message for thread ID:", thread_id, "Message:", user_input)

  # Start run and send run ID back to ManyChat
  client.beta.threads.messages.create(thread_id=thread_id,
                                      role="user",
                                      content=user_input)
  run = client.beta.threads.runs.create(thread_id=thread_id,
                                        assistant_id=assistant_id)
  print("Run started with ID:", run.id)
  return jsonify({"run_id": run.id})


# Check status of run
@app.route('/check', methods=['POST'])
def check_run_status():
  print('check')
  data = request.json
  thread_id = data.get('thread_id')
  run_id = data.get('run_id')
  if not thread_id or not run_id:
    print("Error: Missing thread_id or run_id in /check")
    return jsonify({"response": "error"})

  # Start timer ensuring no more than 9 seconds, ManyChat timeout is 10s

  completed = False
  start_time = time.time()
  while time.time() - start_time < 9:
    run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                   run_id=run_id)
    print("Checking run status:", run_status.status)

    if run_status.status == 'completed':
      completed = True
      break

    elif run_status.status == 'requires_action':
      return jsonify({
        "status": "requires_action"
      })

    time.sleep(0.5)

  if completed:
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    message_content = messages.data[0].content[0].text
      
    # Remove annotations
    annotations = message_content.annotations
    for annotation in annotations:
      message_content.value = message_content.value.replace(
          annotation.text, '')

    print("Run completed, returning response")

    final_msg = message_content.value

    if len(final_msg) > 999:
      final_msg = final_msg[:999]

    return jsonify({
        "response": final_msg,
        "status": "completed"
    })

  print("Run timed out")
  return jsonify({"response": "timeout"})

@app.route('/action_functions', methods=['POST'])
def run_functions():

  data = request.json
  thread_id = data.get('thread_id')
  run_id = data.get('run_id')
  if not thread_id or not run_id:
    print("Error: Missing thread_id or run_id in /check")
    return jsonify({"response": "error"})

  run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                   run_id=run_id)
    
  tool_output_array = []
    # write logic for function calling
  for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
    tool_call_id = tool_call.id
    function_name = tool_call.function.name
    function_arg = tool_call.function.arguments



    if tool_call.function.name == "checkAvailabilityAndReserve":
        # Extract arguments
        args = json.loads(tool_call.function.arguments)
        number_of_guests = args["number_of_guests"]
        reservation_start = args["reservation_start"]

        # Call your function
        output = functions.check_availability_and_reserve(number_of_guests, reservation_start)

    tool_output_array.append({"tool_call_id": tool_call_id, "output": output})


  run = client.beta.threads.runs.submit_tool_outputs(
    thread_id = thread_id,
    run_id=run_id,
    tool_outputs=tool_output_array
  )

  return jsonify({
    "run_id": run.id,
    "status": run.status
  })


