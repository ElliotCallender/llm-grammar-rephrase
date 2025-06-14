import flet as ft
import asyncio
import pyperclip
import llm_interact
import random
import json

SCREEN_WIDTH = 1920

async def main(page: ft.Page):
    def cycle_list(list, currentIndex, interval=1):
        if (len(list) <= 1):
            return currentIndex
        else:
            newIndex = (currentIndex + interval) % (len(list) -1)
            return newIndex
    
    def cycle_api_key(interval=1):
        keyObj = llm_interact.unwrap_json(llm_interact.API_KEY_DIR)
        keys = keyObj['keys']
        currentIndex = int(keyObj['currentIndex'])
        newIndex = cycle_list(keys, currentIndex, interval)
        keyObj['currentIndex'] = str(newIndex)
        with open(llm_interact.API_KEY_DIR, 'w') as f:
            json.dump(keyObj, f, indent=4)
        return keys[newIndex]

    def cycle_text(textField, interval=1):
        currentIndex = textField.data['text']['index']
        newIndex = cycle_list(textField.data['text']['list'], currentIndex, interval)
        textField.data['text']['index'] = newIndex
        if (textField.data['prompt'] != 'None'): # Str 'None' is intentionally set for bottommost text fields
            textField.value = textField.data['text']['list'][newIndex]
            change_text(ft.ControlEvent(control=textField, data='placeholder', name='placeholder', target=textField.uid, page=page)) # Trigger change_text manually
        textField.update()

    def cycle_prompt(textField, interval=1):
        currentIndex = textField.data['prompt']['index']
        promptSection = textField.data['prompt']['section']
        newIndex = cycle_list(prompts[promptSection], currentIndex, interval)
        textField.data['prompt']['index'] = newIndex
        change_text(ft.ControlEvent(control=textField, data='placeholder', name='placeholder', target=textField.uid, page=page)) # Trigger change_text manually
        textField.update()
        
    def set_rand_prompts(prompts):
        first = {'index': cycle_list(prompts['first'], 0, random.randint(0,100)), 'section': 'first'}
        second = {'index': cycle_list(prompts['second'], 0, random.randint(0,100)), 'section': 'second'}
        third = {'index': cycle_list(prompts['third'], 0, random.randint(0,100)), 'section': 'third'}
        firstGrmr = {'index': cycle_list(prompts['grammar'], 0, random.randint(0,100)), 'section': 'grammar'}
        secndGrmr = {'index': cycle_list(prompts['grammar'], 0, random.randint(0,100)), 'section': 'grammar'}
        thirdGrmr = {'index': cycle_list(prompts['grammar'], 0, random.randint(0,100)), 'section': 'grammar'}
        return first, second, third, firstGrmr, secndGrmr, thirdGrmr
    
    prompts = llm_interact.unwrap_json()
    firstPrompt, secondPrompt, thirdPrompt, firstGrmrPrompt, secondGrmrPrompt, thirdGrmrPrompt = set_rand_prompts(prompts)
    rephraseWrapper = llm_interact.GET_WRAPPER(prompts)

    def get_prompts():
        prompts = llm_interact.unwrap_json()
        return prompts
    
    def get_descriptors():
        prompts = get_prompts()
        descriptors = {
            'first': prompts['first']['descriptors'],
            'second': prompts['second']['descriptors'],
            'third': prompts['third']['descriptors']
        }
        return descriptors
    descriptorList = get_descriptors() # Get initial descriptors

    def save_descriptors(e):
        prompts = get_prompts()
        section, value = e.control.data['section'], e.control.value
        e.control.data['descriptorList'][section] = value
        descriptors = e.control.data['descriptorList']
        for section in ['first', 'second', 'third']:
            prompts[section]['descriptors'] = descriptors[section]
        with open(llm_interact.PROMPTS_DIR, 'w') as f:
            json.dump(prompts, f, indent=4)

    def focus_chngdesc(e): # Change descriptors when focus changes
        data = e.control.data
        prompts = get_prompts()
        section = e.control.label.lower()
        if section in ['first', 'second', 'third']:
            descriptors = prompts[section]['descriptors']
            descriptorTextField = data['text']['descriptorTextField']
            descriptorTextField.data['descriptorList'] = get_descriptors()
            descriptorTextField.data['section'] = section
            descriptorTextField.value = descriptors
            descriptorTextField.update()


    def change_text(e):
        data = e.control.data
        prompts = get_prompts()
        prompt = data.get('prompt') if isinstance(data, dict) else None # Copilot checking dict structure
        if (e.control.value == ''): # If the text field is empty, set it to the first item in the list
            textIndex = data['text']['index'] # Allows handling of multiple text fields
            e.control.value = data['text']['list'][textIndex]
        else:
            data['text']['list'][0] = e.control.value
        if (prompt is not None): # 'None' is intentionally set for bottommost text fields
            promptText = prompts[prompt['section']][str(prompt['index'])]
            data['text']['displayed'].value = llm_interact.parse_via_concat(promptText['beginning'], e.control.value, promptText['end'])
            data['text']['displayed'].update()
        else:
            print('No values satisfied for change_text() in llm_flet.py')

    async def send_to_deepseek(e):
        data = e.control.data
        displayedText = data['text']['displayed']
        prompts = get_prompts()
        if (e.control.label == 'Copy?'): # Hacky! Assumes the label texts of bottommost input fields are always 'Copy?'
            pyperclip.copy(displayedText)
        else: # If not 'Copy?', must build prompt and send to DeepSeek.
            promptIndex = str(data['prompt']['index'])
            prompt = prompts[data['prompt']['section']][promptIndex]
            sys = prompt['system']
            userExample = prompt['user']
            assistantExample = prompt['assistant']
            visibleRequest = displayedText.value
            if (e.control.label != 'Change syntax?'):
                wrappedRequest = llm_interact.wrap_with_rephrase(rephraseWrapper, visibleRequest)
            else:
                wrappedRequest = visibleRequest
            finalFormat = llm_interact.parse_to_json(sys, userExample, assistantExample, wrappedRequest)
            key = cycle_api_key() # Returns the next API key and handles cycling
            response = await llm_interact.get_response_async(fullPrompt=finalFormat, apiKey=key)
            grammar = data['grammar'] # ft.TextField control
            if (grammar.data['text']['list'][0] == ''):
                grammar.data['text']['list'][0] = response
            else:
                grammar.data['text']['list'].append(response)
            grammar.on_change(ft.ControlEvent(control=grammar, data='placeholder', name='placeholder', target=grammar.uid, page=page)) # This is a hack to trigger the on_change event manually.
            grammar.update() #TODO: Momentarily change field color

    async def submit_text(e):
        page.run_task(send_to_deepseek, e)

    # Text fields to display the core request to send to DeepSeek
    firstText = ft.Text()
    secondText = ft.Text()
    thirdText = ft.Text()
    firstGrmrText = ft.Text()
    secondGrmrText = ft.Text()
    thirdGrmrText = ft.Text()
    firstGrmrText2 = ft.Text()
    secondGrmrText2 = ft.Text()
    thirdGrmrText2 = ft.Text()

    descriptors = ft.TextField(
                col=12,
                multiline=True,
                shift_enter=True,
                min_lines=16,
                max_lines=16,
                border=ft.InputBorder.NONE,
                filled=False,
                data={
                    'descriptorList': descriptorList,
                    'section': 'first'
                },
                on_change=save_descriptors
                )


    # Aforementioned input fields
    # These change grammar of raw deepseek responses
    # Defined in reverse order because of reference dependencies
    firstGrammar2 = ft.TextField(
                col=4,
                label="Copy?",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': None,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': firstGrmrText2 # unused
                    }
                },
                on_change=change_text,
                on_submit=submit_text)

    secondGrammar2 = ft.TextField(
                col=3,
                label="Copy?",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': None,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': secondGrmrText2 # unused
                    }
                },
                on_change=change_text,
                on_submit=submit_text)

    thirdGrammar2 = ft.TextField(
                col=3,
                label="Copy?",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': None,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': thirdGrmrText2 # unused
                    }
                },
                on_change=change_text,
                on_submit=submit_text)
    

    firstGrammar = ft.TextField(
                col=3,
                label="Change syntax?",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': firstGrmrPrompt,
                    'grammar': firstGrammar2,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': firstGrmrText
                    } 
                },
                on_change=change_text,
                on_submit=submit_text)
    
    secondGrammar = ft.TextField(
                col=3,
                label="Change syntax?",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': secondGrmrPrompt,
                    'grammar': secondGrammar2,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': secondGrmrText
                    }
                },
                on_change=change_text,
                on_submit=submit_text)
    
    thirdGrammar = ft.TextField(
                col=3,
                label="Change syntax?",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': thirdGrmrPrompt,
                    'grammar': thirdGrammar2,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': thirdGrmrText
                    }
                },
                on_change=change_text,
                on_submit=submit_text)
    

    first = ft.TextField(
                col=3,
                label="first",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': firstPrompt,
                    'grammar': firstGrammar,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': firstText,
                        'descriptorTextField': descriptors
                    }
                },
                on_change=change_text,
                on_submit=submit_text,
                on_focus=focus_chngdesc)
    
    second = ft.TextField(
                col=3,
                label="second",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': secondPrompt,
                    'grammar': secondGrammar,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': secondText,
                        'descriptorTextField': descriptors
                    }
                },
                on_change=change_text,
                on_submit=submit_text,
                on_focus=focus_chngdesc)
    
    third = ft.TextField(
                col=3,
                label="third",
                multiline=True,
                shift_enter=True,
                min_lines=4,
                max_lines=4,
                border=ft.InputBorder.NONE,
                filled=True,
                data={
                    'prompt': thirdPrompt,
                    'grammar': thirdGrammar,
                    'text': {
                        'index': 0,
                        'list': [''],
                        'displayed': thirdText,
                        'descriptorTextField': descriptors
                    }
                },
                on_change=change_text,
                on_submit=submit_text,
                on_focus=focus_chngdesc)
    


    # Buttons to cycle through the prompts
    firstCyclePrompt = ft.IconButton(
        icon=ft.Icons.ROTATE_LEFT,
        tooltip="Cycle prompt",
        on_click=lambda e: cycle_prompt(first, 1)
    )
    secondCyclePrompt = ft.IconButton(
        icon=ft.Icons.ROTATE_LEFT,
        tooltip="Cycle prompt",
        on_click=lambda e: cycle_prompt(second, 1)
    )
    thirdCyclePrompt = ft.IconButton(
        icon=ft.Icons.ROTATE_LEFT,
        tooltip="Cycle prompt",
        on_click=lambda e: cycle_prompt(third, 1)
    )
    firstGrmrCyclePrompt = ft.IconButton(
        icon=ft.Icons.ROTATE_LEFT,
        tooltip="Cycle prompt",
        on_click=lambda e: cycle_prompt(firstGrammar, 1)
    )
    secondGrmrCyclePrompt = ft.IconButton(
        icon=ft.Icons.ROTATE_LEFT,
        tooltip="Cycle prompt",
        on_click=lambda e: cycle_prompt(secondGrammar, 1)
    )
    thirdGrmrCyclePrompt = ft.IconButton(
        icon=ft.Icons.ROTATE_LEFT,
        tooltip="Cycle prompt",
        on_click=lambda e: cycle_prompt(thirdGrammar, 1)
    )

    # Buttons to cycle through the text lists
    firstGrmrCycleText = ft.IconButton(
        icon=ft.Icons.TEXT_ROTATE_VERTICAL,
        tooltip="Cycle text list",
        on_click=lambda e: cycle_text(firstGrammar, 1)
    )
    secondGrmrCycleText = ft.IconButton(
        icon=ft.Icons.TEXT_ROTATE_VERTICAL,
        tooltip="Cycle text list",
        on_click=lambda e: cycle_text(secondGrammar, 1)
    )
    thirdGrmrCycleText = ft.IconButton(
        icon=ft.Icons.TEXT_ROTATE_VERTICAL,
        tooltip="Cycle text list",
        on_click=lambda e: cycle_text(thirdGrammar, 1)
    )
    firstGrmrCycleText2 = ft.IconButton(
        icon=ft.Icons.TEXT_ROTATE_VERTICAL,
        tooltip="Cycle text list",
        on_click=lambda e: cycle_text(firstGrammar2, 1)
    )
    secondGrmrCycleText2 = ft.IconButton(
        icon=ft.Icons.TEXT_ROTATE_VERTICAL,
        tooltip="Cycle text list",
        on_click=lambda e: cycle_text(secondGrammar2, 1)
    )
    thirdGrmrCycleText2 = ft.IconButton(
        icon=ft.Icons.TEXT_ROTATE_VERTICAL,
        tooltip="Cycle text list",
        on_click=lambda e: cycle_text(thirdGrammar2, 1)
    )

    textWidth = SCREEN_WIDTH / 3.5 - 20 # Width of text boxes, minus some padding

    firstWithButtons = ft.Row(
        controls=[ft.Container(
            content=first, width=textWidth), firstCyclePrompt])
    secondWithButtons = ft.Row(
        controls=[ft.Container(
            content=second, width=textWidth), secondCyclePrompt])
    thirdWithButtons = ft.Row(
        controls=[ft.Container(
            content=third, width=textWidth), thirdCyclePrompt])
    firstGrmrWithButtons = ft.Row(
        controls=[ft.Container(
            content=firstGrammar, width=textWidth), ft.Column([firstGrmrCyclePrompt, firstGrmrCycleText])])
    secondGrmrWithButtons = ft.Row(
        controls=[ft.Container(
            content=secondGrammar, width=textWidth), ft.Column([secondGrmrCyclePrompt, secondGrmrCycleText])])
    thirdGrmrWithButtons = ft.Row(
        controls=[ft.Container(
            content=thirdGrammar, width=textWidth), ft.Column([thirdGrmrCyclePrompt, thirdGrmrCycleText])])
    firstGrmrWithButtons2 = ft.Row(
        controls=[ft.Container(
            content=firstGrammar2, width=textWidth), ft.Column([firstGrmrCycleText2])])
    secondGrmrWithButtons2 = ft.Row(
        controls=[ft.Container(
            content=secondGrammar2, width=textWidth), ft.Column([secondGrmrCycleText2])])
    thirdGrmrWithButtons2 = ft.Row(
        controls=[ft.Container(
            content=thirdGrammar2, width=textWidth), ft.Column([thirdGrmrCycleText2])])



    # Build layout
    rows = ft.Column(
        spacing=50,
        controls = [
            ft.ResponsiveRow(
                controls = [
                    ft.Column(col = 4, controls = [firstWithButtons, firstText], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Column(col = 4, controls = [secondWithButtons, secondText], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Column(col = 4, controls = [thirdWithButtons, thirdText], alignment=ft.MainAxisAlignment.CENTER)
            ]),
            ft.ResponsiveRow(
                controls = [
                    ft.Column(col = 4, controls = [firstGrmrWithButtons, firstGrmrText], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Column(col = 4, controls = [secondGrmrWithButtons, secondGrmrText], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Column(col = 4, controls = [thirdGrmrWithButtons, thirdGrmrText], alignment=ft.MainAxisAlignment.CENTER)
            ]),
            ft.ResponsiveRow(
                controls = [
                    ft.Column(col = 4, controls = [firstGrmrWithButtons2], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Column(col = 4, controls = [secondGrmrWithButtons2], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Column(col = 4, controls = [thirdGrmrWithButtons2], alignment=ft.MainAxisAlignment.CENTER)
            ]),
            ft.ResponsiveRow(
                controls = [
                    ft.Column(col = 12, controls=[descriptors], alignment=ft.MainAxisAlignment.CENTER)
            ]),
    ])

    page.add(rows)


ft.app(target=main)