/**
 * PaginationControls Component
 * 
 * Reusable pagination controls with page navigation and page size selector
 */

import { getPageRange, hasNextPage, hasPreviousPage } from '../utils/pagination';
import './PaginationControls.css';

const PaginationControls = ({ 
  pagination, 
  currentPage, 
  onPageChange, 
  pageSize, 
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50, 100],
  showPageSize = true 
}) => {
  if (!pagination) return null;

  const { totalPages, count } = pagination;
  
  if (totalPages <= 1 && !showPageSize) return null;

  const pageRange = getPageRange(currentPage, totalPages);
  const hasPrev = hasPreviousPage(pagination);
  const hasNext = hasNextPage(pagination);

  const handlePageClick = (page) => {
    if (page !== currentPage && page >= 1 && page <= totalPages) {
      onPageChange(page);
    }
  };

  const handlePageSizeChange = (e) => {
    const newSize = parseInt(e.target.value, 10);
    if (onPageSizeChange) {
      onPageSizeChange(newSize);
    }
  };

  return (
    <div className="pagination-controls">
      <div className="pagination-info">
        Showing {Math.min(count, (currentPage - 1) * pageSize + 1)} - {Math.min(count, currentPage * pageSize)} of {count} results
      </div>
      
      <div className="pagination-buttons">
        <button 
          className="pagination-btn"
          onClick={() => handlePageClick(1)}
          disabled={!hasPrev}
          title="First page"
        >
          &laquo;
        </button>
        
        <button 
          className="pagination-btn"
          onClick={() => handlePageClick(currentPage - 1)}
          disabled={!hasPrev}
          title="Previous page"
        >
          &lsaquo;
        </button>
        
        {pageRange.map(page => (
          <button
            key={page}
            className={`pagination-btn ${page === currentPage ? 'active' : ''}`}
            onClick={() => handlePageClick(page)}
          >
            {page}
          </button>
        ))}
        
        <button 
          className="pagination-btn"
          onClick={() => handlePageClick(currentPage + 1)}
          disabled={!hasNext}
          title="Next page"
        >
          &rsaquo;
        </button>
        
        <button 
          className="pagination-btn"
          onClick={() => handlePageClick(totalPages)}
          disabled={!hasNext}
          title="Last page"
        >
          &raquo;
        </button>
      </div>

      {showPageSize && onPageSizeChange && (
        <div className="pagination-size">
          <label htmlFor="page-size">Per page:</label>
          <select 
            id="page-size"
            value={pageSize} 
            onChange={handlePageSizeChange}
            className="pagination-size-select"
          >
            {pageSizeOptions.map(size => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};

export default PaginationControls;
