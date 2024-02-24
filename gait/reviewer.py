from openai import OpenAI


class Reviewer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)

    def review(
        self,
        patch: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.2,
    ):
        result = self.client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {
                    "role": "system",
                    "content": """Act as a senior developer who reviews a code change. As a senior developer, your task is to provide constructive feedback and guidance on the quality of a given diff.

Review the individual files and modules. Ignore the changes to automatically generated files in the diff such as .lock, manifest.json, .min.css, snaps, etc.

Assess the clarity of variable and function names and consistent coding style. Evaluate the code's structure, ensuring it follows modular design principles and separates concerns appropriately. Next, analyze the code's efficiency and performance. Look for any potential bottlenecks, unnecessary computations, or inefficient algorithms. Suggest optimizations or alternative approaches that can enhance the code's speed and resource usage. Take into account factors such as the potential impact on the overall system, the likelihood of introducing new bugs or security vulnerabilities, code readability, maintainability, test coverage, efficiency, adherence to best practices, security, and overall design patterns. Your review should focus on identifying potential issues and suggesting improvements. If the PR lacks robust tests, provide suggestions for additional tests.

If any issues are spotted, highlight them, explain the problem, and provide code suggestions. When you suggest new code, keep it simple and adhere to the principles mentioned above. Do not suggest commenting on the code, except adding docs.

Remember to approach the code review process with a constructive and helpful mindset, aiming to assist the developer in creating a higher-quality codebase.

Conclude your review by deciding whether you request changes or approve it.""",  # noqa: E501
                },
                {"role": "user", "content": patch},
            ],
            stream=True,
        )
        for chunk in result:
            chunk_content = chunk.choices[0].delta.content
            if chunk_content is None:
                break
            print(chunk_content, end="", flush=True)
