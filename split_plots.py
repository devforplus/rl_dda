from PIL import Image
import os


def split_and_enhance_image(image_path, output_dir="split_plots"):
    """
    Splits a 2x2 plot image into 4 separate, larger, and clearer images.

    Args:
        image_path (str): The path to the input image file.
        output_dir (str): The directory to save the output images.
    """
    try:
        original_image = Image.open(image_path)
    except FileNotFoundError:
        print(f"Error: The file '{image_path}' was not found.")
        print(
            "Please make sure the path is correct and the script is run from the workspace root directory."
        )
        return

    width, height = original_image.size

    # Add a small margin to avoid cutting off titles/labels near the center
    margin = 5
    mid_width = width // 2
    mid_height = height // 2

    # Coordinates for the 4 plots (left, upper, right, lower)
    # Adjusted with margin to slightly overlap and not miss central labels.
    coords = {
        "top_left": (0, 0, mid_width + margin, mid_height + margin),
        "top_right": (mid_width - margin, 0, width, mid_height + margin),
        "bottom_left": (0, mid_height - margin, mid_width + margin, height),
        "bottom_right": (mid_width - margin, mid_height - margin, width, height),
    }

    plot_titles = {
        "top_left": "01_rewards_by_skill_level",
        "top_right": "02_survival_time_by_skill_level",
        "bottom_left": "03_scores_by_skill_level",
        "bottom_right": "04_kills_by_skill_level",
    }

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: '{output_dir}'")

    resize_factor = 2

    for name, coord in coords.items():
        cropped_image = original_image.crop(coord)

        # Attempt to auto-trim whitespace from the borders
        try:
            bbox = cropped_image.getbbox()
            if bbox:
                cropped_image = cropped_image.crop(bbox)
        except Exception:
            # If trimming fails (e.g., solid color image), use the original crop
            pass

        new_size = (
            cropped_image.width * resize_factor,
            cropped_image.height * resize_factor,
        )
        # Image.Resampling.LANCZOS is a high-quality filter for resizing
        resized_image = cropped_image.resize(new_size, Image.Resampling.LANCZOS)

        output_filename = f"{plot_titles[name]}.png"
        output_path = os.path.join(output_dir, output_filename)

        # Save with high DPI for better quality
        resized_image.save(output_path, dpi=(300, 300))

        print(f"Saved: '{output_path}'")


if __name__ == "__main__":
    # This path is relative to your workspace root (C:\Users\USER\RL_DDA)
    input_image_path = (
        "src\\src\\models\\training_results_skill_comparison_20250813_092736.png"
    )

    # The output directory will be created in your workspace root
    output_directory = "training_results_split"

    print(f"Attempting to read image from: '{input_image_path}'")
    if os.path.exists(input_image_path):
        split_and_enhance_image(input_image_path, output_directory)
    else:
        print(f"FATAL ERROR: Image file not found at '{input_image_path}'.")
        print(
            "Please ensure the file exists and you are running the script from the project root folder."
        )


