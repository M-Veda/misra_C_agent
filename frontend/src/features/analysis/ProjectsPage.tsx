import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useCreateProjectMutation, useProjectsQuery } from "@/api/hooks/useAnalysisQuery";

export function ProjectsPage() {
  const navigate = useNavigate();
  const { data: projects, isLoading } = useProjectsQuery();
  const createProject = useCreateProjectMutation();
  const [name, setName] = useState("STM32 Sample");
  const [rootPath, setRootPath] = useState("/workspace/samples/bare-metal-stm32");
  const [compileCommandsPath, setCompileCommandsPath] = useState(
    "/workspace/samples/bare-metal-stm32/compile_commands.json",
  );

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const project = await createProject.mutateAsync({
      name,
      root_path: rootPath,
      toolchain_profile_id: "clang-host",
      compile_commands_path: compileCommandsPath,
    });
    navigate(`/projects/${project.id}/analysis`);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
      <section className="panel p-6">
        <h3 className="text-lg font-semibold text-white">Import Project</h3>
        <p className="mt-2 text-sm text-slate-400">
          Register a project with compile_commands.json for Clang AST extraction.
        </p>
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm text-slate-300">
            Project Name
            <input
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="block text-sm text-slate-300">
            Root Path
            <input
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2"
              value={rootPath}
              onChange={(event) => setRootPath(event.target.value)}
            />
          </label>
          <label className="block text-sm text-slate-300">
            compile_commands.json
            <input
              className="mt-1 w-full rounded-lg border border-surface-border bg-surface px-3 py-2"
              value={compileCommandsPath}
              onChange={(event) => setCompileCommandsPath(event.target.value)}
            />
          </label>
          <button
            type="submit"
            className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white"
            disabled={createProject.isPending}
          >
            {createProject.isPending ? "Creating..." : "Import Project"}
          </button>
        </form>
      </section>

      <section className="panel p-6">
        <h3 className="text-lg font-semibold text-white">Projects</h3>
        <div className="mt-4 space-y-3">
          {isLoading && <p className="text-sm text-slate-400">Loading projects...</p>}
          {projects?.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}/analysis`}
              className="block rounded-lg border border-surface-border bg-surface px-4 py-3 hover:border-accent"
            >
              <p className="font-medium text-white">{project.name}</p>
              <p className="mt-1 text-xs text-slate-400">{project.root_path}</p>
            </Link>
          ))}
          {!isLoading && projects?.length === 0 && (
            <p className="text-sm text-slate-400">No projects imported yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}
