import gradio as gr

from src.assistant.chatbot import ChatBot
from src.utils.ui_settings import UISettings

with gr.Blocks() as demo:
    with gr.Row() as row_one:
        chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            type="messages",
            height=725,
        )
        chatbot.like(UISettings.feedback, None, None) # **Adding like/dislike icons

    with gr.Row():
        input_txt = gr.Textbox(
            lines=3,
            scale=8,
            placeholder="Enter text here.",
            container=False,
        )

    with gr.Row() as row_two:
        text_submit_btn = gr.Button(value="Submit text")
        clear_button = gr.ClearButton([input_txt, chatbot])

    text_submit_btn.click(
        fn=ChatBot.respond,
        inputs=[chatbot, input_txt],
        outputs=[input_txt, chatbot],
        queue=True
    ).then(
        lambda: gr.Textbox(interactive=True), None, [input_txt], queue=False
    )


if __name__ == "__main__":
    demo.launch(debug=True)
