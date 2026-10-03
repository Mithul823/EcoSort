from gemini_service import create_client, EcoSortError


def main():
    try:
        with create_client() as client:
            print("Models supporting generateContent:")
            for model in client.models.list():
                if "generateContent" in (model.supported_actions or []):
                    print(model.name)
    except EcoSortError as error:
        print(error)
    except Exception:
        print("Could not list models. Check your key, network, and Gemini availability.")


if __name__ == "__main__":
    main()
