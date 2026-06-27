type ProjectOption = {
  id: number;
  title: string;
};

type ProjectSelectorProps = {
  projects: ProjectOption[];
  selectedProjectId?: number;
  onSelect: (projectId: number) => void;
};

export function ProjectSelector({ projects, selectedProjectId, onSelect }: ProjectSelectorProps) {
  return (
    <label>
      Project
      <select value={selectedProjectId ?? ''} onChange={(event) => onSelect(Number(event.target.value))}>
        <option value="" disabled>
          Select a project
        </option>
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.title}
          </option>
        ))}
      </select>
    </label>
  );
}
