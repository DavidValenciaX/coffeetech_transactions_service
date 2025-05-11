import logging
import os
from logging.handlers import RotatingFileHandler
import sys

def setup_logger():
    """
    Configure the logging system for the application.
    Creates a logs directory if it doesn't exist.
    Sets up console and file handlers with appropriate formatting.
    If file handler setup fails, logs a warning to the console and continues.
    """
    log_file_path = None # Initialize log_file_path
    try:
        # Calculate the project root directory (coffeetech_services)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        # Create logs directory in the project root (outside transactions_service)
        logs_dir = os.path.join(project_root, "logs")

        if not os.path.exists(logs_dir):
            try:
                os.makedirs(logs_dir)
            except OSError as e:
                # Handle potential race condition or permission error during dir creation
                if not os.path.isdir(logs_dir):
                    # Log directly to stderr as logger might not be fully set up
                    print(f"ERROR: Failed to create log directory {logs_dir}: {e}", file=sys.stderr)
                    # Re-raise if it's not a directory exists error or permission issue we can maybe ignore
                    # Depending on requirements, you might want to exit or continue without file logging
                    raise # Or decide to proceed without file logging

        # --- Basic Root Logger Configuration ---
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO) # Default level

        # Clear any existing handlers to avoid duplicates during reloads
        if root_logger.handlers:
            root_logger.handlers.clear()

        # --- Console Handler (Always attempt to add this first) ---
        try:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_format)
            root_logger.addHandler(console_handler)
        except Exception as e:
            # If even console handler fails, print to stderr
            print(f"CRITICAL ERROR: Failed to set up console logging: {e}", file=sys.stderr)
            # Depending on policy, might want to exit or raise
            # return None # Indicate failure

        # --- File Handler (Attempt to add, log warning on failure) ---
        try:
            log_file_path = os.path.join(logs_dir, "coffeetech_transactions.log")
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3,
                encoding='utf-8' # Good practice to specify encoding
            )
            file_handler.setLevel(logging.INFO)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_format)
            root_logger.addHandler(file_handler)
            # Log the path for verification only if file handler was successful
            root_logger.info(f"Logging to file: {log_file_path}")

        except Exception as e:
            # Use the already configured root_logger (which should have console handler)
            # Check if console handler was added successfully before logging warning
            if any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
                root_logger.warning(f"Failed to set up file logging to {log_file_path}: {e}. Logging will proceed only to console.")
            else:
                # Fallback if console handler also failed
                print(f"WARNING: Failed to set up file logging to {log_file_path}: {e}. Console logging also failed.", file=sys.stderr)


    except Exception as e:
        # Catch any unexpected error during the initial setup phase (like path calculation)
        print(f"CRITICAL ERROR during logger setup: {e}", file=sys.stderr)
        # Return a basic logger or None to indicate failure
        # Setting up a minimal fallback logger
        root_logger = logging.getLogger("fallback_logger")
        if not root_logger.handlers: # Avoid adding handler multiple times if called again after failure
            fallback_handler = logging.StreamHandler(sys.stderr)
            fallback_handler.setLevel(logging.ERROR)
            fallback_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fallback_handler.setFormatter(fallback_formatter)
            root_logger.addHandler(fallback_handler)
            root_logger.error(f"Logger setup failed: {e}. Using fallback stderr logger.")
        return root_logger # Return the fallback

    return root_logger