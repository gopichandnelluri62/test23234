# Use an official lightweight Python 12 image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install gunicorn explicitly to ensure it is available in the container
RUN pip install --no-cache-dir gunicorn

# Install any other needed packages from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set the command to run the application using gunicorn
# Use the exec form with /bin/sh -c to ensure the $PORT
# environment variable is expanded correctly. This is the most
# robust method for both local and cloud environments.
CMD ["/bin/sh", "-c", "/usr/local/bin/gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 \"agent:app\""]
