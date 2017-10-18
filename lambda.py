"""
Proxa, the hands-free virtual lab assistant, is a Protocols.io skill for Amazon's Alexa.

The full source code is available on GitHub at https://github.com/mfcovington/proxa.
"""

import json
import os
import urllib.parse
import urllib.request

PROTOCOLS_IO_ACCESS_TOKEN = os.environ['PROTOCOLS_IO_ACCESS_TOKEN']
# --------------- Helpers that build all of the responses ----------------


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------

def get_welcome_response():
    """ Initialize the session """

    card_title = 'Welcome'
    speech_output = ('Welcome to Proxa. Please tell me what protocol to '
                     'search for by saying, search protocols i o for cell '
                     'culture')
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = ('Please tell me what protocol to search for by saying, '
                     'search protocols i o for cell culture.')
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = 'Session Ended'
    speech_output = 'I hope your experiment is successful. Have a nice day!'
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def set_keyword_in_session(intent, session):
    """ Sets the keyword in the session and prepares the speech to reply to the
    user.
    """

    card_title = intent['name']
    session_attributes = {}
    should_end_session = False

    keyword = intent['slots']['Keyword']['value']
    session_attributes['keyword'] = keyword

    url = 'https://protocols.io/api/open/get_protocols'
    values = {
        'access_token': PROTOCOLS_IO_ACCESS_TOKEN,
        'key': keyword,
    }

    data = urllib.parse.urlencode(values).encode('utf-8')
    req = urllib.request.Request(url, data)
    response = urllib.request.urlopen(req)
    the_page = response.read()

    total_results = json.loads(the_page)['total_results']
    session_attributes['total_results'] = total_results

    protocol_list = json.loads(the_page)['protocols']
    session_attributes['protocol_list'] = protocol_list

    speech_output = ('I have found {} protocols related to {}. Say list '
                     'protocols to hear the {} protocols'.format(
                         total_results, keyword, keyword))
    reprompt_text = ('You can ask me your search term by saying, what am I '
                     'searching for?')

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_keyword_from_session(intent, session):
    session_attributes = session.get('attributes', {})
    reprompt_text = None

    if 'keyword' in session.get('attributes', {}):
        keyword = session['attributes']['keyword']
        speech_output = ('Your search term is {}. Say list protocols to hear '
                         'the {} protocols'.format(keyword, keyword))
        should_end_session = False
    else:
        speech_output = ('I am not sure what your search term is. You can '
                         'say, search protocols i o for cell culture.')
        should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


def get_protocol_list_from_session(intent, session):
    session_attributes = session.get('attributes', {})
    reprompt_text = None

    if 'protocol_list' in session.get('attributes', {}):
        protocol_list = session['attributes']['protocol_list']
        keyword = session['attributes']['keyword']
        speech_output = 'Here are the first {} {} protocols. '.format(
            len(protocol_list), keyword)

        for i, protocol in enumerate(protocol_list):
            speech_output = '{}. number {}: {}'.format(
                speech_output, i + 1, protocol['protocol_name'])

        should_end_session = False
    else:
        speech_output = ('I am not sure what your search term is. You can '
                         'say, search protocols i o for cell culture.')
        should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


def get_protocol_step_from_session(intent, session):
    session_attributes = session.get('attributes', {})
    reprompt_text = None

    # TEMPORARY
    url = 'https://protocols.io/api/open/get_protocol_json'
    protocol_id = '8256'
    values = {
        'access_token': PROTOCOLS_IO_ACCESS_TOKEN,
        'protocol_id': protocol_id,
    }
    data = urllib.parse.urlencode(values).encode('utf-8')
    req = urllib.request.Request(url, data)
    response = urllib.request.urlopen(req)
    the_page = response.read()
    protocol = json.loads(the_page)['protocol']
    protocol_name = protocol['protocol_name']
    protocol_description = protocol['description']
    steps = protocol['steps']
    total_steps = len(steps)
    step_list = []
    for s in steps:
        for c in s['components']:
            if c['name'] == 'Description':
                step_list.append(c['data'])
    session['attributes']['step_list'] = step_list
    session['attributes']['total_steps'] = total_steps
    if 'next_step' not in session.get('attributes', {}):
        session['attributes']['next_step'] = 0
    # END TEMPORARY

    if 'step_list' in session.get('attributes', {}):
        step_list = session['attributes']['step_list']
        next_step = session['attributes']['next_step']
        total_steps = session['attributes']['total_steps']

        # TEMPORARY
        speech_output = ''
        if next_step == 0:
            speech_output = ('I have found protocol ID {}: {}. This protocol '
                             'has {} steps. {} '.format(
                                 protocol_id, protocol_name, total_steps,
                                 protocol_description))
        # TEMPORARY

        if next_step >= total_steps:
            speech_output = 'Protocol Finished! Good bye.'
            should_end_session = True
        else:
            speech_output = speech_output + 'Step number {}: {} '.format(
                next_step + 1, step_list[next_step])
            session_attributes['next_step'] = next_step + 1
            should_end_session = False

    else:
        speech_output = ('I am not sure what you protocol you want. You can '
                         'say, search protocols i o for cell culture.')
        should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print('on_session_started requestId={}, sessionId={}'.format(
        session_started_request['requestId'], session['sessionId']))


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print('on_launch requestId={}, sessionId={}'.format(
        launch_request['requestId'], session['sessionId']))
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print('on_intent requestId={}, sessionId={}'.format(
        intent_request['requestId'], session['sessionId']))

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == 'MyKeywordIsIntent':
        return set_keyword_in_session(intent, session)
    elif intent_name == 'WhatsMyKeywordIntent':
        return get_keyword_from_session(intent, session)
    elif intent_name == 'WhatsMyProtocolListIntent':
        return get_protocol_list_from_session(intent, session)
    elif intent_name == 'ReadProtocolStepIntent':
        return get_protocol_step_from_session(intent, session)
    elif intent_name == 'AMAZON.HelpIntent':
        return get_welcome_response()
    elif intent_name in ['AMAZON.CancelIntent', 'AMAZON.StopIntent']:
        return handle_session_end_request()
    else:
        raise ValueError('Invalid intent')


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print('on_session_ended requestId={}, sessionId={}'.format(
        session_ended_request['requestId'], session['sessionId']))
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print('event.session.application.applicationId={}'.format(
        event['session']['application']['applicationId']))

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == 'LaunchRequest':
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == 'IntentRequest':
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == 'SessionEndedRequest':
        return on_session_ended(event['request'], event['session'])
