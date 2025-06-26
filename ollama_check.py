import subprocess

def query_ollama(prompt):

    result = subprocess.run(

        ["ollama", "run", "phi"],

        input=prompt.encode(),

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        timeout=300

    )

    return result.stdout.decode()

def test_model():

    test_prompt = "What is AI?"

    print("Sending prompt:", test_prompt)

    try:

        response = query_ollama(test_prompt)

        print("Model response:\n", response)

    except Exception as e:

        print("❌ Model failed:", e)

# Run test when script is run directly

if __name__ == "__main__":

    test_model()
 