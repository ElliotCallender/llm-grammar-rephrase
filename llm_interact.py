import deepseek
from deepseek import DeepSeekAPI
import json
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor

PROMPTS_DIR = 'prompts.json'
API_KEY_DIR = 'api_keys.json'

def get_prompt(prompts, section, index):
	prompt_obj = prompts[section][index]
	return prompt_obj

def get_api_keys(dir=API_KEY_DIR, index=0):
	keyObj = unwrap_json(dir)
	return keyObj

def unwrap_json(dir=PROMPTS_DIR):
	jsonTxt = ''
	with open(dir) as f:
		jsonTxt = json.load(f)
	return jsonTxt



def parse_via_concat(beginning, content, end):
	return beginning + content + end

def GET_WRAPPER(prompts):
	return prompts['rephraseWrapper']

def wrap_with_rephrase(wrapper, core): # rephraseWrapper is a dict
	return wrapper['beginning'] + core + wrapper['end']

def parse_to_json(systemPrompt, userExample, assistantExample, coreRequest):
	msgs = [
		{
			'role': 'system',
			'content': systemPrompt
		},
		{
			'role': 'user',
			'content': userExample
		},
		{
			'role': 'assistant',
			'content': assistantExample
		},
		{
			'role': 'user',
			'content': coreRequest
		}
	]
	return msgs

def get_response_sync(fullPrompt, apiKey, temperature=1.3):
	api_client = DeepSeekAPI(apiKey)
	return api_client.chat_completion(model='deepseek-reasoner', messages=fullPrompt, temperature=temperature)

async def get_response_async(fullPrompt, apiKey, temperature=1.3):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as executor: # async method
        response = await loop.run_in_executor(executor, get_response_sync, fullPrompt, apiKey, temperature)
    return response

#TODO: auto-remove gender
