from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import pandas as pd
import uvicorn
import os

app = FastAPI()

OUTPUT_DIR = "output_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/")
def main():
    return {"message": "Welcome to Crew Scheduling"}

@app.post("/crew")
async def process_scheduling(file: UploadFile = File(...)):
    from validation import prepare_sector_data
    from validation import prepare_crew_data
    from optimizer import develop_scheduling_model

    contents = await file.read()
    sector_df = pd.read_excel(contents, sheet_name='Sectors')
    crew_df = pd.read_excel(contents, sheet_name='Crew', header=1)
    # Usage
    file_path = '/content/Masters and Sectors_Latest_Modified.xlsx'
    crew_quals, crew_roles, cleaned_crew = prepare_crew_data(crew_df)
    sectors = prepare_sector_data(sector_df)
    print(f"Crew qualifications for Brian Higly: {crew_quals.get('Brian Higly')}")

    # print crew name and model for all
    for name, models in crew_quals.items():
        print(f"{name}: {', '.join(models)}")
    
    # Run the model
    final_schedule = develop_scheduling_model(sectors, crew_quals, crew_roles)
    output_path = os.path.join(OUTPUT_DIR, f"FinalSchedule_Latest_Roster")

    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        if isinstance(final_schedule, pd.DataFrame):
            final_schedule.to_excel(writer, sheet_name='Final Schedule', index=False)
        else:
            print(f"Could not generate a schedule: {final_schedule}")
    return FileResponse(output_path, filename=f"FinalSchedule_Latest_Roster.xlsx", media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')