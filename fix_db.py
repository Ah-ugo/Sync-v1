import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv()


async def fix_kyc_data():
    print("🔌 Connecting to MongoDB...")
    mongo_url = os.getenv("MONGODB_URL")
    if not mongo_url:
        print("❌ MONGODB_URL not found in .env")
        return

    client = AsyncIOMotorClient(mongo_url)
    db = client[os.getenv("DATABASE_NAME", "sync")]

    # 1. Fix Invalid KYC Status
    # The error 'Input should be pending, approved or rejected' was caused by 'complete'
    print("🔍 Scanning for invalid KYC statuses...")
    result = await db.kyc_submissions.update_many(
        {"status": "complete"},
        {"$set": {"status": "pending"}}
    )

    if result.modified_count > 0:
        print(f"✅ Fixed {result.modified_count} KYC submissions (changed 'complete' to 'pending').")
    else:
        print("✅ No invalid KYC submissions found.")

    client.close()
    print("👋 Done.")


if __name__ == "__main__":
    asyncio.run(fix_kyc_data())
