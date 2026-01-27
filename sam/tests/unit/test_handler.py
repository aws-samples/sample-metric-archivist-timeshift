import json
import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
import migrate_metric.app as app

@pytest.fixture
def fail_400_events_directory():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    events_dir = os.path.join(current_dir, 'events/fail_400')
    if not os.path.exists(events_dir):
        pytest.skip("Events directory not found")
    else:
        print(f"Events directory: {events_dir}")
    return events_dir


@pytest.fixture
def success_events_directory():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    events_dir = os.path.join(current_dir, 'events/success')
    if not os.path.exists(events_dir):
        pytest.skip("Events directory not found")
    else:
        print(f"Events directory: {events_dir}")
    return events_dir

def test_success_events_return_200(success_events_directory):
    event_files = [f for f in os.listdir(success_events_directory) if f.endswith('.json')]
    
    if not event_files:
        pytest.skip("No event files found in events directory")
    
    for filename in event_files:
        event_path = os.path.join(success_events_directory, filename)
        
        try:
            with open(success_events_directory + '/../sqs-skeleton.json', 'r') as f:
                skeleton = json.load(f)
            with open(event_path, 'r') as f:
                fileStr = f.read()
                body = json.loads(fileStr)
                skeleton['Records'][0]['body'] = json.dumps(body)
                event = skeleton
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {filename}: {str(e)}")
        except Exception as e:
            pytest.fail(f"Error reading {filename}: {str(e)}")
            
        try:
            response = app.lambda_handler(event, {})
            assert isinstance(response, dict), f"Event {filename}: Response should be a dictionary"
            assert len(response['batchItemFailures']) == 0, f"batchItemFailures are unexpectedly present."
        except Exception as e:
            pytest.fail(f"Handler failed for {filename}: {str(e)}")

def test_fail_400_events_return_400(fail_400_events_directory):
    event_files = [f for f in os.listdir(fail_400_events_directory) if f.endswith('.json')]
    
    if not event_files:
        pytest.skip("No event files found in events directory")
    
    for filename in event_files:
        event_path = os.path.join(fail_400_events_directory, filename)
        
        try:
            with open(fail_400_events_directory + '/../sqs-skeleton.json', 'r') as f:
                skeleton = json.load(f)
            with open(event_path, 'r') as f:
                fileStr = f.read()
                body = json.loads(fileStr)
                skeleton['Records'][0]['body'] = json.dumps(body)
                event = skeleton
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {filename}: {str(e)}")
        except Exception as e:
            pytest.fail(f"Error reading {filename}: {str(e)}")
            
        try:
            response = app.lambda_handler(event, {})
            assert isinstance(response, dict), f"Event {filename}: Response should be a dictionary"
            assert len(response['batchItemFailures']) == 1, f"batchItemFailures is unexpectedly missing."
        except Exception as e:
            pytest.fail(f"Handler failed for {filename}: {str(e)}")