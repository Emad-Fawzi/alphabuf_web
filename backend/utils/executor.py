import concurrent.futures

# Global thread pool executor for running blocking operations across the app
shared_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
