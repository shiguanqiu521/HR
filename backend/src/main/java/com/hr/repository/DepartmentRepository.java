package com.hr.repository;

import com.hr.model.Department;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DepartmentRepository extends JpaRepository<Department, Long> {

    Optional<Department> findByIdAndDeleted(Long id, Integer deleted);

    boolean existsByNameAndDeleted(String name, Integer deleted);

    @Query("SELECT d FROM Department d WHERE d.deleted = 0 AND (:name IS NULL OR d.name LIKE %:name%) ORDER BY d.createdAt DESC")
    List<Department> search(@Param("name") String name);

    @Query("SELECT COUNT(d) FROM Department d WHERE d.deleted = 0")
    long countActive();
}
