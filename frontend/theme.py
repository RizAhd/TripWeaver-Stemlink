import gradio as gr
from gradio.themes.utils import colors, fonts, sizes

INK = "#12212e"
SLATE = "#5b6b7a"
SEA = "#0e7c86"
SEA_DEEP = "#0a5f68"
SAND = "#f6f3ec"
PAPER = "#ffffff"
LINE = "#e2ded4"

FONT_STACK = "Fraunces"
BODY_STACK = "Karla"


class TripWeaverTheme(gr.themes.Base):
    def __init__(self):
        super().__init__(
            primary_hue=colors.teal,
            secondary_hue=colors.amber,
            neutral_hue=colors.stone,
            text_size=sizes.text_md,
            spacing_size=sizes.spacing_md,
            radius_size=sizes.radius_lg,
            font=(fonts.LocalFont(BODY_STACK), "ui-sans-serif", "system-ui", "sans-serif"),
            font_mono=(fonts.LocalFont("IBM Plex Mono"), "ui-monospace", "monospace"),
        )

        self.set(
            body_background_fill=SAND,
            body_background_fill_dark="#101a21",
            body_text_color=INK,
            body_text_color_dark="#e8e3d9",
            body_text_color_subdued=SLATE,

            background_fill_primary=PAPER,
            background_fill_primary_dark="#17242d",
            background_fill_secondary=SAND,
            background_fill_secondary_dark="#101a21",

            block_background_fill=PAPER,
            block_background_fill_dark="#17242d",
            block_border_width="1px",
            block_border_color=LINE,
            block_border_color_dark="#26353f",
            block_radius="14px",
            block_shadow="0 1px 2px rgba(18, 33, 46, 0.05)",
            block_padding="18px",
            block_label_background_fill="transparent",
            block_label_text_color=SLATE,
            block_label_text_weight="600",

            border_color_primary=LINE,
            border_color_primary_dark="#26353f",
            panel_background_fill=PAPER,
            panel_background_fill_dark="#17242d",
            layout_gap="14px",

            button_primary_background_fill=SEA,
            button_primary_background_fill_hover=SEA_DEEP,
            button_primary_text_color=PAPER,
            button_primary_border_color=SEA,
            button_primary_shadow="none",
            button_secondary_background_fill=PAPER,
            button_secondary_background_fill_hover=SAND,
            button_secondary_text_color=INK,
            button_secondary_border_color=LINE,
            button_large_radius="10px",
            button_small_radius="8px",
            button_large_text_weight="600",
            button_transition="all 0.15s ease",
            button_transform_hover="translateY(-1px)",

            input_background_fill=PAPER,
            input_background_fill_dark="#17242d",
            input_border_color=LINE,
            input_border_color_dark="#26353f",
            input_border_color_focus=SEA,
            input_radius="10px",
            input_shadow="none",
            input_placeholder_color=SLATE,

            link_text_color=SEA,
            link_text_color_hover=SEA_DEEP,
            shadow_drop="0 1px 2px rgba(18, 33, 46, 0.05)",
            chatbot_text_size=sizes.text_md,
        )

        self.custom_css = """
        .prose h1, .prose h2, .prose h3 {font-family: 'Fraunces', Georgia, serif;}
        """


HEAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Karla:wght@400;500;600&display=swap" rel="stylesheet">
<meta name="description" content="TripWeaver plans flights and hotels in one conversation.">
<meta name="theme-color" content="#0e7c86">
"""
