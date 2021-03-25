async def finish(generator):
    """
    Yield all items from an async generator.
    """
    async for _event, *_data in generator:
        pass
